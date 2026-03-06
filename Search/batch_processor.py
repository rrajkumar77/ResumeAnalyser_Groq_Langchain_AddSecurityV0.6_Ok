"""
Batch Candidate Processing Module
==================================

Enables bulk resume screening against a single JD with:
- Parallel processing for speed
- Ranked candidate list with scores
- Auto-filtering by configurable thresholds
- Export to CSV/Excel for further analysis
- Progress tracking and error handling

Use Case:
Upload 1 JD + 50 resumes → Get ranked list in minutes instead of hours
"""

import io
import zipfile
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pandas as pd

from enhanced_semantic_matcher import EnhancedSemanticSkillMatcher, ExperienceDepth


@dataclass
class CandidateResult:
    """Result for a single candidate analysis."""
    candidate_id: str
    filename: str
    fit_score: float
    validated_skills_count: int
    priority_skills_validated: int
    expert_skills_count: int
    proficient_skills_count: int
    missing_priority_skills: List[str]
    top_strengths: List[str]
    top_gaps: List[str]
    recommendation: str
    analysis_timestamp: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for DataFrame export."""
        return {
            "Candidate ID": self.candidate_id,
            "Filename": self.filename,
            "Fit Score": f"{self.fit_score:.0%}",
            "Validated Skills": self.validated_skills_count,
            "Priority Skills Match": self.priority_skills_validated,
            "Expert Skills": self.expert_skills_count,
            "Proficient Skills": self.proficient_skills_count,
            "Missing Priority Skills": ", ".join(self.missing_priority_skills) if self.missing_priority_skills else "None",
            "Top Strengths": ", ".join(self.top_strengths[:3]) if self.top_strengths else "N/A",
            "Top Gaps": ", ".join(self.top_gaps[:3]) if self.top_gaps else "N/A",
            "Recommendation": self.recommendation,
            "Analysis Date": self.analysis_timestamp
        }


@dataclass
class BatchProcessingResult:
    """Complete batch processing result."""
    total_candidates: int
    processed_successfully: int
    failed_candidates: int
    results: List[CandidateResult]
    processing_time_seconds: float
    jd_summary: str
    priority_skills: List[str]
    
    def get_ranked_results(self, min_fit_score: float = 0.0) -> List[CandidateResult]:
        """Get results ranked by fit score, filtered by threshold."""
        filtered = [r for r in self.results if r.fit_score >= min_fit_score]
        return sorted(filtered, key=lambda x: x.fit_score, reverse=True)
    
    def get_statistics(self) -> Dict:
        """Get summary statistics."""
        if not self.results:
            return {}
        
        fit_scores = [r.fit_score for r in self.results]
        
        return {
            "total_candidates": self.total_candidates,
            "processed": self.processed_successfully,
            "failed": self.failed_candidates,
            "avg_fit_score": sum(fit_scores) / len(fit_scores),
            "max_fit_score": max(fit_scores),
            "min_fit_score": min(fit_scores),
            "strong_matches_75plus": sum(1 for s in fit_scores if s >= 0.75),
            "good_matches_60_to_75": sum(1 for s in fit_scores if 0.60 <= s < 0.75),
            "weak_matches_below_60": sum(1 for s in fit_scores if s < 0.60),
            "processing_time": f"{self.processing_time_seconds:.1f}s"
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame."""
        return pd.DataFrame([r.to_dict() for r in self.results])
    
    def export_to_csv(self, filepath: str):
        """Export results to CSV file."""
        df = self.to_dataframe()
        df.to_csv(filepath, index=False)
    
    def export_to_excel(self, filepath: str):
        """Export results to Excel with formatting."""
        df = self.to_dataframe()
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Candidates', index=False)
            
            # Add summary sheet
            stats = self.get_statistics()
            summary_df = pd.DataFrame([
                {"Metric": k, "Value": v} for k, v in stats.items()
            ])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)


class BatchCandidateProcessor:
    """
    Processes multiple candidate resumes against a single JD in parallel.
    """
    
    def __init__(self, matcher: Optional[EnhancedSemanticSkillMatcher] = None):
        """
        Initialize batch processor.
        
        Args:
            matcher: EnhancedSemanticSkillMatcher instance (creates default if None)
        """
        self.matcher = matcher or EnhancedSemanticSkillMatcher()
    
    def process_batch(
        self,
        jd_text: str,
        resume_texts: Dict[str, str],
        priority_skills: Optional[List[str]] = None,
        max_workers: int = 4,
        progress_callback=None
    ) -> BatchProcessingResult:
        """
        Process multiple resumes against a JD in parallel.
        
        Args:
            jd_text: Job Description text
            resume_texts: Dictionary mapping candidate_id -> resume_text
            priority_skills: Optional list of priority skills
            max_workers: Number of parallel workers
            progress_callback: Optional callback function(current, total)
            
        Returns:
            BatchProcessingResult with ranked candidates
        """
        start_time = datetime.now()
        results = []
        failed_count = 0
        
        # Extract JD summary
        jd_summary = jd_text[:200] + "..." if len(jd_text) > 200 else jd_text
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_candidate = {
                executor.submit(
                    self._process_single_candidate,
                    candidate_id,
                    jd_text,
                    resume_text,
                    priority_skills
                ): candidate_id
                for candidate_id, resume_text in resume_texts.items()
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_candidate):
                candidate_id = future_to_candidate[future]
                completed += 1
                
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    failed_count += 1
                    print(f"Failed to process {candidate_id}: {e}")
                
                # Progress callback
                if progress_callback:
                    progress_callback(completed, len(resume_texts))
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        return BatchProcessingResult(
            total_candidates=len(resume_texts),
            processed_successfully=len(results),
            failed_candidates=failed_count,
            results=results,
            processing_time_seconds=processing_time,
            jd_summary=jd_summary,
            priority_skills=priority_skills or []
        )
    
    def _process_single_candidate(
        self,
        candidate_id: str,
        jd_text: str,
        resume_text: str,
        priority_skills: Optional[List[str]]
    ) -> CandidateResult:
        """
        Process a single candidate resume.
        
        Args:
            candidate_id: Unique candidate identifier
            jd_text: Job Description text
            resume_text: Resume text
            priority_skills: Priority skills list
            
        Returns:
            CandidateResult
        """
        # Run enhanced analysis
        report = self.matcher.analyze_with_priorities(
            jd_text=jd_text,
            resume_text=resume_text,
            priority_skills=priority_skills
        )
        
        # Count priority skills validated
        priority_set = set(s.lower().strip() for s in (priority_skills or []))
        priority_validated = sum(
            1 for s in report.validated_skills
            if s.skill_name.lower() in priority_set
        )
        
        # Count expert/proficient skills
        expert_count = sum(
            1 for s in report.validated_skills
            if hasattr(s, 'experience_depth') and s.experience_depth == ExperienceDepth.EXPERT
        )
        proficient_count = sum(
            1 for s in report.validated_skills
            if hasattr(s, 'experience_depth') and s.experience_depth == ExperienceDepth.PROFICIENT
        )
        
        # Identify missing priority skills
        missing_priority = [
            s.skill_name for s in report.missing_skills
            if s.skill_name.lower() in priority_set
        ]
        
        # Top strengths (highest hands-on scores)
        top_strengths = [
            s.skill_name for s in sorted(
                report.validated_skills,
                key=lambda x: getattr(x, 'hands_on_score', 0),
                reverse=True
            )[:5]
        ]
        
        # Top gaps
        top_gaps = [s.skill_name for s in report.missing_skills[:5]]
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            report.overall_relevance_score,
            priority_validated,
            len(priority_skills or []),
            missing_priority,
            expert_count
        )
        
        return CandidateResult(
            candidate_id=candidate_id,
            filename=candidate_id,  # Can be updated with actual filename
            fit_score=report.overall_relevance_score,
            validated_skills_count=len(report.validated_skills),
            priority_skills_validated=priority_validated,
            expert_skills_count=expert_count,
            proficient_skills_count=proficient_count,
            missing_priority_skills=missing_priority,
            top_strengths=top_strengths,
            top_gaps=top_gaps,
            recommendation=recommendation,
            analysis_timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    
    def _generate_recommendation(
        self,
        fit_score: float,
        priority_validated: int,
        total_priority: int,
        missing_priority: List[str],
        expert_count: int
    ) -> str:
        """Generate hiring recommendation based on analysis."""
        if fit_score >= 0.85 and priority_validated == total_priority:
            return "🚀 STRONG MATCH - Fast-track to interview"
        elif fit_score >= 0.75 and priority_validated >= total_priority * 0.75:
            return "✅ GOOD MATCH - Recommend phone screen"
        elif fit_score >= 0.65:
            if missing_priority:
                return f"⚠️ MODERATE MATCH - Missing: {', '.join(missing_priority[:2])} - Assess depth in interview"
            else:
                return "⚠️ MODERATE MATCH - Recommend technical assessment"
        elif fit_score >= 0.50:
            return "❓ WEAK MATCH - Consider for junior roles or training program"
        else:
            return "❌ POOR MATCH - Does not meet minimum requirements"
    
    def process_from_zip(
        self,
        jd_text: str,
        zip_file_bytes: bytes,
        priority_skills: Optional[List[str]] = None,
        supported_extensions: Tuple[str, ...] = ('.txt', '.pdf', '.docx'),
        progress_callback=None
    ) -> BatchProcessingResult:
        """
        Process resumes from a ZIP file.
        
        Args:
            jd_text: Job Description text
            zip_file_bytes: ZIP file bytes
            priority_skills: Priority skills list
            supported_extensions: Tuple of supported file extensions
            progress_callback: Progress callback function
            
        Returns:
            BatchProcessingResult
        """
        resume_texts = {}
        
        # Extract resumes from ZIP
        with zipfile.ZipFile(io.BytesIO(zip_file_bytes), 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                filename = file_info.filename
                
                # Skip directories and unsupported files
                if file_info.is_dir() or not filename.lower().endswith(supported_extensions):
                    continue
                
                try:
                    # Read file content
                    with zip_ref.open(filename) as file:
                        file_bytes = file.read()
                        
                        # Extract text based on file type
                        if filename.lower().endswith('.txt'):
                            resume_text = file_bytes.decode('utf-8', errors='ignore')
                        elif filename.lower().endswith('.pdf'):
                            resume_text = self._extract_text_from_pdf_bytes(file_bytes)
                        elif filename.lower().endswith('.docx'):
                            resume_text = self._extract_text_from_docx_bytes(file_bytes)
                        else:
                            continue
                        
                        resume_texts[filename] = resume_text
                
                except Exception as e:
                    print(f"Failed to extract {filename}: {e}")
        
        # Process extracted resumes
        return self.process_batch(
            jd_text=jd_text,
            resume_texts=resume_texts,
            priority_skills=priority_skills,
            progress_callback=progress_callback
        )
    
    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes."""
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_parts = [page.get_text() for page in doc]
        return " ".join(text_parts).strip()
    
    def _extract_text_from_docx_bytes(self, docx_bytes: bytes) -> str:
        """Extract text from DOCX bytes."""
        import docx
        doc = docx.Document(io.BytesIO(docx_bytes))
        text_parts = [p.text for p in doc.paragraphs]
        return " ".join(text_parts).strip()


# ==================== Utility Functions ====================

def create_batch_summary_report(result: BatchProcessingResult) -> str:
    """
    Create a human-readable summary report.
    
    Args:
        result: BatchProcessingResult
        
    Returns:
        Formatted summary string
    """
    stats = result.get_statistics()
    ranked = result.get_ranked_results()
    
    report = f"""
BATCH PROCESSING SUMMARY
{'=' * 80}

Total Candidates: {stats['total_candidates']}
Processed Successfully: {stats['processed']}
Failed: {stats['failed']}
Processing Time: {stats['processing_time']}

FIT SCORE DISTRIBUTION
{'-' * 80}
Average Fit Score: {stats['avg_fit_score']:.0%}
Highest Fit Score: {stats['max_fit_score']:.0%}
Lowest Fit Score: {stats['min_fit_score']:.0%}

Strong Matches (75%+): {stats['strong_matches_75plus']}
Good Matches (60-75%): {stats['good_matches_60_to_75']}
Weak Matches (<60%): {stats['weak_matches_below_60']}

TOP 10 CANDIDATES
{'-' * 80}
{'Rank':<6} {'Candidate':<30} {'Fit':<8} {'Priority':<10} {'Expert':<8} {'Recommendation'}
{'-' * 80}
"""
    
    for rank, candidate in enumerate(ranked[:10], 1):
        report += f"{rank:<6} {candidate.candidate_id[:30]:<30} {candidate.fit_score:<8.0%} {candidate.priority_skills_validated:<10} {candidate.expert_skills_count:<8} {candidate.recommendation}\n"
    
    report += f"\n{'=' * 80}\n"
    
    return report


if __name__ == "__main__":
    # Example usage
    print("Batch Candidate Processor - Ready for Integration")
