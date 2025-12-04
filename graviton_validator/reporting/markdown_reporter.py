"""
Markdown report generator for Graviton compatibility analysis results.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from .base import ReportGenerator
from .json_reporter import JSONReporter
from ..models import AnalysisResult, CompatibilityStatus


class MarkdownReporter(ReportGenerator):
    """
    Markdown report generator that creates human-readable reports.
    Uses JSONReporter internally for data structuring.
    """
    
    def __init__(self, include_metadata: bool = True, include_toc: bool = True):
        """
        Initialize Markdown reporter.
        
        Args:
            include_metadata: Whether to include metadata section
            include_toc: Whether to include table of contents
        """
        self.include_metadata = include_metadata
        self.include_toc = include_toc
        self.json_reporter = JSONReporter(include_metadata=include_metadata)
    
    def generate_report(self, analysis_result: AnalysisResult, output_path: Optional[str] = None) -> str:
        """
        Generate Markdown report from analysis results.
        
        Args:
            analysis_result: AnalysisResult to generate report from
            output_path: Optional path to write report to file
            
        Returns:
            Markdown report content as string
        """
        # Get structured data from JSON reporter
        data = self.json_reporter.get_structured_data(analysis_result)
        
        # Build markdown content
        markdown_content = self._build_markdown_report(data)
        
        # Write to file if path provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        
        return markdown_content
    
    def get_format_name(self) -> str:
        """Get the name of the report format."""
        return "markdown"
    
    def _build_markdown_report(self, data: Dict[str, Any]) -> str:
        """
        Build complete Markdown report from structured data.
        
        Args:
            data: Structured report data from JSON reporter
            
        Returns:
            Complete Markdown report as string
        """
        sections = []
        
        # Title and metadata
        sections.append(self._build_title_section(data))
        
        if self.include_metadata and "metadata" in data:
            sections.append(self._build_metadata_section(data["metadata"]))
        
        # Table of contents
        if self.include_toc:
            sections.append(self._build_toc())
        
        # Executive summary
        sections.append(self._build_summary_section(data["summary"]))
        
        # Compatibility overview
        sections.append(self._build_overview_section(data["statistics"]))
        
        # Detailed results
        sections.append(self._build_detailed_results_section(data["components"]))
        
        # Recommendations
        sections.append(self._build_recommendations_section(data))
        
        # Errors and warnings
        if data["errors"]:
            sections.append(self._build_errors_section(data["errors"]))
        
        return "\n\n".join(sections)
    
    def _build_title_section(self, data: Dict[str, Any]) -> str:
        """Build title section."""
        summary = data["summary"]
        metadata = data.get("metadata", {})
        status_emoji = "✅" if not summary["has_issues"] else "⚠️"
        
        title_content = f"""# {status_emoji} Graviton Compatibility Report

**Analysis completed with {summary['compatible']} compatible, {summary['incompatible']} incompatible, and {summary['unknown']} unknown components out of {summary['total_components']} total.**"""
        
        # Add OS and SBOM file info if available
        if metadata.get("detected_os") or metadata.get("sbom_file"):
            title_content += "\n\n"
            if metadata.get("detected_os"):
                title_content += f"**Detected OS:** {metadata['detected_os']}\n\n"
            if metadata.get("sbom_file"):
                title_content += f"**SBOM File:** {metadata['sbom_file']}\n\n"
        
        return title_content
    
    def _build_metadata_section(self, metadata: Dict[str, Any]) -> str:
        """Build metadata section."""
        return f"""## 📋 Report Information

- **Generated:** {metadata['generated_at']}
- **Generator:** {metadata['generator']} v{metadata['version']}
- **Format:** {metadata['report_format']}"""
    
    def _build_toc(self) -> str:
        """Build table of contents."""
        return """## 📑 Table of Contents

- [Executive Summary](#-executive-summary)
- [Compatibility Overview](#-compatibility-overview)
- [Detailed Results](#-detailed-results)
- [Recommendations](#-recommendations)"""
    
    def _build_summary_section(self, summary: Dict[str, Any]) -> str:
        """Build executive summary section."""
        compatibility_rate = summary["compatibility_rate"]
        processing_time = summary["processing_time_seconds"]
        
        # Determine overall status
        if compatibility_rate == 100:
            status_text = "🎉 **Excellent!** All components are compatible with Graviton."
        elif compatibility_rate >= 80:
            status_text = "✅ **Good!** Most components are compatible with Graviton."
        elif compatibility_rate >= 50:
            status_text = "⚠️ **Moderate.** Some components may need attention for Graviton compatibility."
        else:
            status_text = "❌ **Attention Required!** Many components have compatibility issues."
        
        return f"""## 📊 Executive Summary

{status_text}

### Key Metrics

| Metric | Value |
|--------|-------|
| **Total Components** | {summary['total_components']} |
| **Compatible** | {summary['compatible']} ({compatibility_rate}%) |
| **Incompatible** | {summary['incompatible']} |
| **Unknown Status** | {summary['unknown']} |
| **Processing Time** | {processing_time}s |"""
    
    def _build_overview_section(self, statistics: Dict[str, Any]) -> str:
        """Build compatibility overview section."""
        status_breakdown = statistics["status_breakdown"]
        sbom_breakdown = statistics["sbom_breakdown"]
        upgrade_recs = statistics["upgrade_recommendations"]
        
        # Build status breakdown table
        status_table = """### Compatibility Status Breakdown

| Status | Count | Components |
|--------|-------|------------|"""
        
        for status, info in status_breakdown.items():
            emoji = {"compatible": "✅", "incompatible": "❌", "needs_upgrade": "🔄", "needs_verification": "🔍", "unknown": "❓"}[status]
            components_list = ", ".join(info["components"][:5])  # Show first 5
            if len(info["components"]) > 5:
                components_list += f" (+{len(info['components']) - 5} more)"
            
            status_table += f"\n| {emoji} {status.title()} | {info['count']} | {components_list} |"
        
        # Build SBOM breakdown
        sbom_table = "\n\n### Analysis by SBOM File\n\n| SBOM File | Detected OS | OS Support | Compatible | Incompatible | Unknown |\n|-----------|-------------|------------|------------|--------------|---------|"
        
        for sbom_file, counts in sbom_breakdown.items():
            detected_os = counts.get("detected_os", "N/A")
            os_support = counts.get("os_support_status", "Unknown")
            support_icon = "✅" if os_support == "Supported" else "❌" if os_support == "Not Supported" else "❓"
            sbom_table += f"\n| `{sbom_file}` | {detected_os} | {support_icon} {os_support} | {counts['compatible']} | {counts['incompatible']} | {counts['unknown']} |"
        
        # Build upgrade summary
        upgrade_summary = f"""

### Upgrade Path Summary

- **Components with upgrade path:** {upgrade_recs['upgrade_available']}
- **Components without upgrade path:** {upgrade_recs['no_upgrade_path']}"""
        
        return f"""## 🔍 Compatibility Overview

{status_table}{sbom_table}{upgrade_summary}"""
    
    def _build_detailed_results_section(self, components: List[Dict[str, Any]]) -> str:
        """Build detailed results section."""
        sections = ["## 📋 Detailed Results"]
        
        # Group components by status
        by_status = {"compatible": [], "incompatible": [], "needs_upgrade": [], "needs_verification": [], "unknown": []}
        for comp in components:
            status = comp["compatibility"]["status"]
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(comp)
        
        # Build each status section
        for status in ["incompatible", "needs_upgrade", "needs_verification", "unknown", "compatible"]:
            if not by_status.get(status):
                continue
                
            emoji = {"compatible": "✅", "incompatible": "❌", "needs_upgrade": "🔄", "needs_verification": "🔍", "unknown": "❓"}[status]
            sections.append(f"### {emoji} {status.title()} Components ({len(by_status[status])})")
            
            for comp in by_status[status]:
                sections.append(self._build_component_detail(comp))
        
        return "\n\n".join(sections)
    
    def _build_component_detail(self, component: Dict[str, Any]) -> str:
        """Build detailed information for a single component."""
        name = component["name"]
        version = component.get("version", "N/A")
        comp_type = component.get("type", "unknown")
        source = component.get("source_sbom", "unknown")
        
        compat = component["compatibility"]
        status = compat["status"]
        
        # Build header
        detail = f"#### {name} v{version}\n\n"
        
        # Build info table
        detail += f"""| Property | Value |
|----------|-------|
| **Type** | {comp_type} |
| **Source SBOM** | `{source}` |
| **Status** | {status} |"""
        
        # Add matched name if different
        if "matched_name" in component and component["matched_name"] != name:
            detail += f"\n| **Matched As** | {component['matched_name']} |"
        
        # Add compatibility details
        if compat.get("current_version_supported") is not None:
            detail += f"\n| **Current Version Supported** | {'Yes' if compat['current_version_supported'] else 'No'} |"
        
        if compat.get("minimum_supported_version"):
            detail += f"\n| **Minimum Supported Version** | {compat['minimum_supported_version']} |"
        
        if compat.get("recommended_version"):
            detail += f"\n| **Recommended Version** | {compat['recommended_version']} |"
        
        if compat.get("confidence_level") is not None and compat["confidence_level"] < 1.0:
            confidence_pct = int(compat["confidence_level"] * 100)
            detail += f"\n| **Confidence Level** | {confidence_pct}% |"
        
        # Add notes if present
        if compat.get("notes"):
            detail += f"\n\n**Notes:** {compat['notes']}"
        
        # Add properties if present
        if component.get("properties"):
            detail += "\n\n**Properties:**\n"
            for prop, value in component["properties"].items():
                detail += f"- **{prop}:** {value}\n"
        
        return detail
    
    def _build_recommendations_section(self, data: Dict[str, Any]) -> str:
        """Build recommendations section."""
        components = data["components"]
        statistics = data["statistics"]
        
        recommendations = ["## 🎯 Recommendations"]
        
        # General recommendations based on overall status
        summary = data["summary"]
        if summary["incompatible"] > 0:
            recommendations.append("### 🔧 Immediate Actions Required")
            
            incompatible_components = [c for c in components if c["compatibility"]["status"] == "incompatible"]
            
            # Components with upgrade paths
            with_upgrades = [c for c in incompatible_components if c["compatibility"].get("recommended_version")]
            if with_upgrades:
                recommendations.append("#### Components with Available Upgrades")
                for comp in with_upgrades:
                    current = comp.get("version", "unknown")
                    recommended = comp["compatibility"]["recommended_version"]
                    recommendations.append(f"- **{comp['name']}**: Upgrade from v{current} to v{recommended}")
            
            # Components without upgrade paths
            without_upgrades = [c for c in incompatible_components if not c["compatibility"].get("recommended_version")]
            if without_upgrades:
                recommendations.append("\n#### Components Requiring Investigation")
                for comp in without_upgrades:
                    recommendations.append(f"- **{comp['name']}**: No known Graviton-compatible version available")
        
        if summary["unknown"] > 0:
            recommendations.append("### ❓ Components Requiring Research")
            unknown_components = [c for c in components if c["compatibility"]["status"] == "unknown"]
            for comp in unknown_components:
                recommendations.append(f"- **{comp['name']}**: Verify Graviton compatibility manually")
        
        # Migration strategy
        if summary["incompatible"] > 0 or summary["unknown"] > 0:
            recommendations.append("""### 📋 Migration Strategy

1. **Phase 1**: Update components with known compatible versions
2. **Phase 2**: Research and test unknown components
3. **Phase 3**: Find alternatives for incompatible components
4. **Phase 4**: Validate entire application on Graviton instances""")
        
        # Success case
        if summary["compatible"] == summary["total_components"]:
            recommendations.append("### 🎉 Ready for Graviton!")
            recommendations.append("All components are compatible. You can proceed with Graviton migration.")
        
        return "\n\n".join(recommendations)
    
    def _build_errors_section(self, errors: List[str]) -> str:
        """Build errors and warnings section."""
        section = ["## ⚠️ Errors and Warnings"]
        
        for i, error in enumerate(errors, 1):
            section.append(f"{i}. {error}")
        
        return "\n\n".join(section)