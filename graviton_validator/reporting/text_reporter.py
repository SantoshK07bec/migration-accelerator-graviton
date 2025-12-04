"""
Human-readable text report generator for Graviton compatibility analysis results.
"""

import sys
from typing import Dict, List, Optional, Any

from .base import ReportGenerator
from .json_reporter import JSONReporter
from ..models import AnalysisResult


class HumanReadableReporter(ReportGenerator):
    """
    Human-readable text report generator for console output.
    Uses JSONReporter internally for data structuring and includes color coding.
    """
    
    # ANSI color codes
    COLORS = {
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'MAGENTA': '\033[95m',
        'CYAN': '\033[96m',
        'WHITE': '\033[97m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
        'RESET': '\033[0m'
    }
    
    # Status symbols and colors
    STATUS_CONFIG = {
        'compatible': {'symbol': '✅', 'color': 'GREEN'},
        'incompatible': {'symbol': '❌', 'color': 'RED'},
        'needs_upgrade': {'symbol': '🔄', 'color': 'YELLOW'},
        'needs_verification': {'symbol': '🔍', 'color': 'CYAN'},
        'needs_version_verification': {'symbol': '🔍', 'color': 'MAGENTA'},
        'unknown': {'symbol': '❓', 'color': 'YELLOW'}
    }
    
    def __init__(self, use_colors: bool = None, width: int = 80, detailed: bool = False):
        """
        Initialize human-readable text reporter.
        
        Args:
            use_colors: Whether to use ANSI color codes. Auto-detects if None.
            width: Console width for formatting (default: 80)
            detailed: Whether to include detailed component results (default: False)
        """
        if use_colors is None:
            # Auto-detect color support
            self.use_colors = self._supports_color()
        else:
            self.use_colors = use_colors
        
        self.width = width
        self.detailed = detailed
        self.json_reporter = JSONReporter(include_metadata=True)
    
    def generate_report(self, analysis_result: AnalysisResult, output_path: Optional[str] = None) -> str:
        """
        Generate human-readable text report from analysis results.
        
        Args:
            analysis_result: AnalysisResult to generate report from
            output_path: Optional path to write report to file
            
        Returns:
            Text report content as string
        """
        # Get structured data from JSON reporter
        data = self.json_reporter.get_structured_data(analysis_result)
        
        # Build text content
        text_content = self._build_text_report(data)
        
        # Write to file if path provided (without colors for file output)
        if output_path:
            # Strip colors for file output
            clean_content = self._strip_colors(text_content)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(clean_content)
        
        return text_content
    
    def get_format_name(self) -> str:
        """Get the name of the report format."""
        return "text"
    
    def _supports_color(self) -> bool:
        """
        Auto-detect if the terminal supports color output.
        
        Returns:
            True if colors are supported, False otherwise
        """
        import os
        
        # Check for common CI environments that support colors (independent of TTY)
        ci_with_colors = ['GITHUB_ACTIONS', 'GITLAB_CI', 'BUILDKITE']
        if any(os.environ.get(var) for var in ci_with_colors):
            return True
        
        # Check if stdout is a TTY and not redirected
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return False
        
        # Check environment variables for terminal color support
        term = os.environ.get('TERM', '').lower()
        if 'color' in term or term in ['xterm', 'xterm-256color', 'screen']:
            return True
        
        return False
    
    def _colorize(self, text: str, color: str) -> str:
        """
        Apply color to text if colors are enabled.
        
        Args:
            text: Text to colorize
            color: Color name from COLORS dict
            
        Returns:
            Colorized text or original text if colors disabled
        """
        if not self.use_colors or color not in self.COLORS:
            return text
        
        return f"{self.COLORS[color]}{text}{self.COLORS['RESET']}"
    
    def _strip_colors(self, text: str) -> str:
        """
        Remove ANSI color codes from text.
        
        Args:
            text: Text with potential color codes
            
        Returns:
            Text with color codes removed
        """
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def _build_text_report(self, data: Dict[str, Any]) -> str:
        """
        Build complete text report from structured data.
        
        Args:
            data: Structured report data from JSON reporter
            
        Returns:
            Complete text report as string
        """
        sections = []
        
        # Header
        sections.append(self._build_header(data))
        
        # Executive summary
        sections.append(self._build_summary_section(data["summary"]))
        
        # Quick overview
        sections.append(self._build_overview_section(data["statistics"]))
        
        # Detailed results (only if detailed mode is enabled)
        if self.detailed:
            sections.append(self._build_detailed_results_section(data["components"]))
        
        # Key findings and recommendations
        sections.append(self._build_recommendations_section(data))
        
        # Errors and warnings
        if data["errors"]:
            sections.append(self._build_errors_section(data["errors"]))
        
        # Footer
        if "metadata" in data:
            sections.append(self._build_footer(data["metadata"]))
        
        return "\n\n".join(sections)
    
    def _build_header(self, data: Dict[str, Any]) -> str:
        """Build report header."""
        summary = data["summary"]
        metadata = data.get("metadata", {})
        
        # Determine overall status
        if not summary["has_issues"]:
            status_text = self._colorize("ALL COMPATIBLE", "GREEN")
            status_symbol = "🎉"
        elif summary["incompatible"] > summary["unknown"]:
            status_text = self._colorize("ISSUES FOUND", "RED")
            status_symbol = "⚠️"
        else:
            status_text = self._colorize("REVIEW NEEDED", "YELLOW")
            status_symbol = "🔍"
        
        title = f"{status_symbol} GRAVITON COMPATIBILITY REPORT - {status_text}"
        separator = "=" * len(self._strip_colors(title))
        
        header_lines = [
            self._colorize(separator, 'BOLD'),
            self._colorize(title, 'BOLD'),
            self._colorize(separator, 'BOLD')
        ]
        
        # Add OS and SBOM file info if available
        if metadata.get("detected_os") or metadata.get("sbom_file"):
            header_lines.append("")
            if metadata.get("detected_os"):
                header_lines.append(f"Detected OS: {self._colorize(metadata['detected_os'], 'CYAN')}")
            if metadata.get("sbom_file"):
                header_lines.append(f"SBOM File: {metadata['sbom_file']}")
        
        return "\n".join(header_lines)
    
    def _build_summary_section(self, summary: Dict[str, Any]) -> str:
        """Build executive summary section with OS-aware information."""
        total = summary["total_components"]
        compatible = summary["compatible"]
        incompatible = summary["incompatible"]
        unknown = summary["unknown"]
        rate = summary["compatibility_rate"]
        
        # Build summary stats
        needs_version_verification = summary.get("needs_version_verification", 0)
        stats_lines = [
            f"📊 {self._colorize('ANALYSIS SUMMARY', 'BOLD')}",
            "",
            f"   Total Components Analyzed: {self._colorize(str(total), 'BOLD')}",
            f"   Compatible:               {self._colorize(str(compatible), 'GREEN')} ({rate}%)",
            f"   Incompatible:             {self._colorize(str(incompatible), 'RED')}",
        ]
        
        if needs_version_verification > 0:
            stats_lines.append(f"   Needs Version Verification: {self._colorize(str(needs_version_verification), 'MAGENTA')}")
        
        stats_lines.extend([
            f"   Unknown Status:           {self._colorize(str(unknown), 'YELLOW')}",
            f"   Processing Time:          {summary['processing_time_seconds']}s"
        ])
        
        # Add OS-aware summary if available
        if "os_summary" in summary:
            os_summary = summary["os_summary"]
            stats_lines.extend([
                "",
                f"🖥️  {self._colorize('OPERATING SYSTEM ANALYSIS', 'BOLD')}",
                f"   Detected OS:              {self._colorize(os_summary.get('detected_os', 'Unknown'), 'CYAN')}",
                f"   System Packages:          {self._colorize(str(os_summary.get('system_packages', 0)), 'GREEN')}",
                f"   Application Packages:     {self._colorize(str(os_summary.get('application_packages', 0)), 'BLUE')}",
                f"   OS Graviton Compatible:   {self._colorize('Yes' if os_summary.get('os_compatible') else 'No', 'GREEN' if os_summary.get('os_compatible') else 'RED')}"
            ])
        
        # Add status message with OS context
        if "os_summary" in summary and summary["os_summary"].get("detected_os"):
            os_name = summary["os_summary"]["detected_os"]
            if rate == 100:
                status_msg = self._colorize(f"🎉 Excellent! All components are Graviton-compatible on {os_name}.", "GREEN")
            elif rate >= 80:
                status_msg = self._colorize(f"✅ Good! Most components are compatible on {os_name}.", "GREEN")
            elif rate >= 50:
                status_msg = self._colorize(f"⚠️  Some components need attention for Graviton compatibility on {os_name}.", "YELLOW")
            else:
                status_msg = self._colorize(f"❌ Significant compatibility issues detected on {os_name}.", "RED")
        else:
            if rate == 100:
                status_msg = self._colorize("🎉 Excellent! All components are Graviton-compatible.", "GREEN")
            elif rate >= 80:
                status_msg = self._colorize("✅ Good! Most components are compatible.", "GREEN")
            elif rate >= 50:
                status_msg = self._colorize("⚠️  Some components need attention for Graviton compatibility.", "YELLOW")
            else:
                status_msg = self._colorize("❌ Significant compatibility issues detected.", "RED")
        
        stats_lines.extend(["", status_msg])
        
        return "\n".join(stats_lines)
    
    def _build_overview_section(self, statistics: Dict[str, Any]) -> str:
        """Build quick overview section."""
        lines = [f"🔍 {self._colorize('QUICK OVERVIEW', 'BOLD')}", ""]
        
        # Status breakdown
        status_breakdown = statistics["status_breakdown"]
        for status, info in status_breakdown.items():
            if info["count"] == 0:
                continue
            
            config = self.STATUS_CONFIG[status]
            symbol = config["symbol"]
            color = config["color"]
            
            components_preview = ", ".join(info["components"][:3])
            if len(info["components"]) > 3:
                components_preview += f" (+{len(info['components']) - 3} more)"
            
            lines.append(f"   {symbol} {self._colorize(status.title(), color)}: {info['count']} components")
            lines.append(f"      {components_preview}")
        
        # SBOM breakdown if multiple files
        sbom_breakdown = statistics["sbom_breakdown"]
        if len(sbom_breakdown) > 1:
            lines.extend(["", "📁 Analysis by SBOM File:"])
            for sbom_file, counts in sbom_breakdown.items():
                total_sbom = counts["compatible"] + counts["incompatible"] + counts["unknown"]
                lines.append(f"   {sbom_file}: {total_sbom} components")
                if counts["compatible"] > 0:
                    lines.append(f"      ✅ {counts['compatible']} compatible")
                if counts["incompatible"] > 0:
                    lines.append(f"      ❌ {counts['incompatible']} incompatible")
                if counts["unknown"] > 0:
                    lines.append(f"      ❓ {counts['unknown']} unknown")
        
        # Upgrade summary
        upgrade_recs = statistics["upgrade_recommendations"]
        if upgrade_recs["upgrade_available"] > 0 or upgrade_recs["no_upgrade_path"] > 0:
            lines.extend(["", "🔄 Upgrade Path Summary:"])
            if upgrade_recs["upgrade_available"] > 0:
                lines.append(f"   ✅ {upgrade_recs['upgrade_available']} components have upgrade paths")
            if upgrade_recs["no_upgrade_path"] > 0:
                lines.append(f"   ❌ {upgrade_recs['no_upgrade_path']} components need alternatives")
        
        return "\n".join(lines)
    
    def _build_detailed_results_section(self, components: List[Dict[str, Any]]) -> str:
        """Build detailed results section."""
        lines = [f"📋 {self._colorize('DETAILED RESULTS', 'BOLD')}", ""]
        
        # Group by status for better organization
        by_status = {"incompatible": [], "needs_upgrade": [], "needs_verification": [], "unknown": [], "compatible": []}
        for comp in components:
            status = comp["compatibility"]["status"]
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(comp)
        
        # Show incompatible first (highest priority)
        for status in ["incompatible", "needs_upgrade", "needs_verification", "unknown", "compatible"]:
            components_list = by_status.get(status, [])
            if not components_list:
                continue
            
            config = self.STATUS_CONFIG[status]
            symbol = config["symbol"]
            color = config["color"]
            
            lines.append(f"{symbol} {self._colorize(f'{status.upper()} COMPONENTS ({len(components_list)})', color)}")
            lines.append("")
            
            for comp in components_list:
                lines.extend(self._format_component_detail(comp))
                lines.append("")
        
        return "\n".join(lines)
    
    def _format_component_detail(self, component: Dict[str, Any]) -> List[str]:
        """Format detailed information for a single component."""
        name = component["name"]
        version = component.get("version", "N/A")
        comp_type = component.get("type", "unknown")
        source = component.get("source_sbom", "unknown")
        
        compat = component["compatibility"]
        status = compat["status"]
        config = self.STATUS_CONFIG[status]
        
        # Component header
        header = f"   {config['symbol']} {self._colorize(f'{name} v{version}', 'BOLD')}"
        lines = [header]
        
        # Basic info
        lines.append(f"      Type: {comp_type}")
        lines.append(f"      Source: {source}")
        
        # Matched name if different
        if "matched_name" in component and component["matched_name"] != name:
            lines.append(f"      Matched as: {component['matched_name']}")
        
        # Runtime analysis information
        props = component.get("properties", {})
        if props.get("runtime_analysis") == "true":
            lines.append(f"      Runtime Analysis: {self._colorize('Yes', 'CYAN')}")
            
            original_version = props.get("original_version")
            if original_version and original_version != version:
                lines.append(f"      Original version: {original_version}")
                lines.append(f"      Working version: {self._colorize(version, 'GREEN')}")
            
            if props.get("fallback_used") == "true":
                lines.append(f"      Fallback used: {self._colorize('Yes', 'YELLOW')} (latest version works)")
        
        # Compatibility details
        if compat.get("current_version_supported") is not None:
            supported = "Yes" if compat["current_version_supported"] else "No"
            color = "GREEN" if compat["current_version_supported"] else "RED"
            lines.append(f"      Current version supported: {self._colorize(supported, color)}")
        
        if compat.get("minimum_supported_version"):
            lines.append(f"      Minimum supported version: {compat['minimum_supported_version']}")
        
        if compat.get("recommended_version"):
            lines.append(f"      Recommended version: {self._colorize(compat['recommended_version'], 'CYAN')}")
        
        if compat.get("confidence_level") is not None and compat["confidence_level"] < 1.0:
            confidence_pct = int(compat["confidence_level"] * 100)
            lines.append(f"      Confidence level: {confidence_pct}%")
        
        # Notes
        if compat.get("notes"):
            lines.append(f"      Notes: {compat['notes']}")
        
        return lines
    
    def _build_recommendations_section(self, data: Dict[str, Any]) -> str:
        """Build recommendations section."""
        lines = [f"🎯 {self._colorize('KEY FINDINGS & RECOMMENDATIONS', 'BOLD')}", ""]
        
        components = data["components"]
        summary = data["summary"]
        
        # Priority actions for incompatible components
        incompatible_components = [c for c in components if c["compatibility"]["status"] == "incompatible"]
        if incompatible_components:
            lines.append(f"{self._colorize('🔧 IMMEDIATE ACTIONS REQUIRED', 'RED')}")
            lines.append("")
            
            # Components with upgrade paths
            with_upgrades = [c for c in incompatible_components if c["compatibility"].get("recommended_version")]
            if with_upgrades:
                lines.append("   📦 Components to Upgrade:")
                for comp in with_upgrades:
                    current = comp.get("version", "unknown")
                    recommended = comp["compatibility"]["recommended_version"]
                    comp_type = comp.get('type', 'unknown')
                    
                    # Show runtime analysis info if available
                    props = comp.get("properties", {})
                    if props.get("runtime_analysis") == "true" and props.get("fallback_used") == "true":
                        original = props.get("original_version", current)
                        lines.append(f"      • {comp['name']}: {original} → {self._colorize(recommended, 'CYAN')} (runtime tested, type: {comp_type})")
                    else:
                        lines.append(f"      • {comp['name']}: {current} → {self._colorize(recommended, 'CYAN')} (type: {comp_type})")
                lines.append("")
            
            # Components without upgrade paths
            without_upgrades = [c for c in incompatible_components if not c["compatibility"].get("recommended_version")]
            if without_upgrades:
                lines.append("   🔍 Components Needing Alternatives:")
                for comp in without_upgrades:
                    comp_type = comp.get('type', 'unknown')
                    lines.append(f"      • {comp['name']} v{comp.get('version', 'unknown')} (type: {comp_type})")
                lines.append("")
        
        # Unknown components
        unknown_components = [c for c in components if c["compatibility"]["status"] == "unknown"]
        if unknown_components:
            lines.append(f"{self._colorize('❓ RESEARCH REQUIRED', 'YELLOW')}")
            lines.append("")
            lines.append("   🔬 Verify Graviton compatibility for:")
            for comp in unknown_components:
                comp_type = comp.get('type', 'unknown')
                lines.append(f"      • {comp['name']} v{comp.get('version', 'unknown')} (type: {comp_type})")
            lines.append("")
        
        # Next steps
        if summary["incompatible"] > 0 or summary["unknown"] > 0:
            lines.append(f"{self._colorize('📋 RECOMMENDED NEXT STEPS', 'BLUE')}")
            lines.append("")
            lines.append("   1. 🔄 Update components with known compatible versions")
            lines.append("   2. 🧪 Test unknown components in development environment")
            lines.append("   3. 🔍 Research alternatives for incompatible components")
            lines.append("   4. ✅ Validate complete application on Graviton instances")
            lines.append("   5. 📊 Monitor performance after migration")
        else:
            lines.append(f"{self._colorize('🎉 READY FOR GRAVITON!', 'GREEN')}")
            lines.append("")
            lines.append("   All components are compatible. You can proceed with confidence!")
            lines.append("   Consider running performance tests to validate the migration.")
        
        return "\n".join(lines)
    
    def _build_errors_section(self, errors: List[str]) -> str:
        """Build errors and warnings section."""
        lines = [f"⚠️  {self._colorize('PROCESSING ERRORS & WARNINGS', 'YELLOW')}", ""]
        
        for i, error in enumerate(errors, 1):
            # Determine error type and color
            if error.lower().startswith("error"):
                color = "RED"
                prefix = "❌"
            elif error.lower().startswith("warning"):
                color = "YELLOW"
                prefix = "⚠️"
            else:
                color = "YELLOW"
                prefix = "ℹ️"
            
            lines.append(f"   {prefix} {self._colorize(error, color)}")
        
        return "\n".join(lines)
    
    def _build_footer(self, metadata: Dict[str, Any]) -> str:
        """Build report footer."""
        separator = "-" * self.width
        
        footer_lines = [
            self._colorize(separator, 'BOLD'),
            f"Generated by {metadata['generator']} v{metadata['version']}",
            f"Report created: {metadata['generated_at']}",
            f"Format: {self.get_format_name()}",
            self._colorize(separator, 'BOLD')
        ]
        
        return "\n".join(footer_lines)


# Alias for backward compatibility
TextReporter = HumanReadableReporter