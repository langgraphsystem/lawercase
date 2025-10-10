"""Grafana Dashboard Configurations.

This module provides pre-configured Grafana dashboards for monitoring
the MegaAgent system. Dashboards are exported as JSON and can be imported
directly into Grafana.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Panel:
    """Grafana panel configuration."""

    title: str
    type: str  # graph, stat, table, gauge, etc.
    targets: list[dict[str, Any]]
    grid_pos: dict[str, int]  # x, y, w, h
    options: dict[str, Any] = field(default_factory=dict)
    field_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert panel to Grafana JSON format."""
        return {
            "title": self.title,
            "type": self.type,
            "gridPos": self.grid_pos,
            "targets": self.targets,
            "options": self.options,
            "fieldConfig": self.field_config,
        }


@dataclass
class GrafanaDashboard:
    """Grafana dashboard configuration."""

    title: str
    panels: list[Panel]
    uid: str | None = None
    tags: list[str] = field(default_factory=list)
    refresh: str = "5s"
    time_from: str = "now-1h"
    time_to: str = "now"

    def to_dict(self) -> dict[str, Any]:
        """Convert dashboard to Grafana JSON format."""
        return {
            "uid": self.uid,
            "title": self.title,
            "tags": self.tags,
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 0,
            "refresh": self.refresh,
            "time": {"from": self.time_from, "to": self.time_to},
            "panels": [panel.to_dict() for panel in self.panels],
        }

    def export_json(self, output_path: str | Path) -> None:
        """Export dashboard to JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w") as f:
            json.dump({"dashboard": self.to_dict()}, f, indent=2)


def create_cache_dashboard() -> GrafanaDashboard:
    """Create dashboard for cache monitoring."""
    panels = [
        # Hit Rate Panel
        Panel(
            title="Cache Hit Rate",
            type="stat",
            grid_pos={"x": 0, "y": 0, "w": 6, "h": 4},
            targets=[
                {
                    "expr": "cache_hit_rate",
                    "refId": "A",
                    "legendFormat": "Hit Rate",
                }
            ],
            options={
                "reduceOptions": {"values": False, "calcs": ["lastNotNull"]},
                "orientation": "auto",
                "textMode": "value_and_name",
                "colorMode": "value",
            },
            field_config={
                "defaults": {
                    "unit": "percentunit",
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": 0, "color": "red"},
                            {"value": 0.5, "color": "yellow"},
                            {"value": 0.8, "color": "green"},
                        ],
                    },
                }
            },
        ),
        # Cache Operations Over Time
        Panel(
            title="Cache Operations",
            type="graph",
            grid_pos={"x": 6, "y": 0, "w": 18, "h": 8},
            targets=[
                {
                    "expr": "rate(cache_hits_total[5m])",
                    "refId": "A",
                    "legendFormat": "Hits/sec",
                },
                {
                    "expr": "rate(cache_misses_total[5m])",
                    "refId": "B",
                    "legendFormat": "Misses/sec",
                },
                {
                    "expr": "rate(cache_sets_total[5m])",
                    "refId": "C",
                    "legendFormat": "Sets/sec",
                },
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "multi"},
            },
        ),
        # Latency Panel
        Panel(
            title="Cache Latency",
            type="graph",
            grid_pos={"x": 0, "y": 8, "w": 12, "h": 8},
            targets=[
                {
                    "expr": "cache_avg_hit_latency_ms",
                    "refId": "A",
                    "legendFormat": "Avg Hit Latency",
                },
                {
                    "expr": "cache_avg_miss_latency_ms",
                    "refId": "B",
                    "legendFormat": "Avg Miss Latency",
                },
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "multi"},
            },
            field_config={"defaults": {"unit": "ms"}},
        ),
        # Error Rate Panel
        Panel(
            title="Cache Errors",
            type="graph",
            grid_pos={"x": 12, "y": 8, "w": 12, "h": 8},
            targets=[
                {
                    "expr": "rate(cache_errors_total[5m])",
                    "refId": "A",
                    "legendFormat": "Errors/sec",
                }
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "single"},
            },
            field_config={
                "defaults": {
                    "color": {"mode": "palette-classic"},
                    "custom": {"fillOpacity": 10},
                }
            },
        ),
    ]

    return GrafanaDashboard(
        title="MegaAgent Cache Performance",
        uid="megaagent-cache",
        panels=panels,
        tags=["cache", "redis", "performance"],
    )


def create_api_dashboard() -> GrafanaDashboard:
    """Create dashboard for API monitoring."""
    panels = [
        # Request Rate
        Panel(
            title="Request Rate",
            type="graph",
            grid_pos={"x": 0, "y": 0, "w": 12, "h": 8},
            targets=[
                {
                    "expr": "sum(rate(mega_agent_http_requests_total[5m])) by (method)",
                    "refId": "A",
                    "legendFormat": "{{method}}",
                }
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "multi"},
            },
        ),
        # Request Latency
        Panel(
            title="Request Latency (p95)",
            type="graph",
            grid_pos={"x": 12, "y": 0, "w": 12, "h": 8},
            targets=[
                {
                    "expr": "histogram_quantile(0.95, sum(rate(mega_agent_http_request_duration_seconds_bucket[5m])) by (le, path))",
                    "refId": "A",
                    "legendFormat": "{{path}}",
                }
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "multi"},
            },
            field_config={"defaults": {"unit": "s"}},
        ),
        # Error Rate by Status
        Panel(
            title="Error Rate by Status",
            type="graph",
            grid_pos={"x": 0, "y": 8, "w": 12, "h": 8},
            targets=[
                {
                    "expr": 'sum(rate(mega_agent_http_requests_total{status=~"5.."}[5m])) by (status)',
                    "refId": "A",
                    "legendFormat": "{{status}}",
                }
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "multi"},
            },
        ),
        # Rate Limit Rejections
        Panel(
            title="Rate Limit Rejections",
            type="stat",
            grid_pos={"x": 12, "y": 8, "w": 6, "h": 4},
            targets=[
                {
                    "expr": "sum(rate(mega_agent_rate_limit_rejections_total[5m]))",
                    "refId": "A",
                    "legendFormat": "Rejections/sec",
                }
            ],
            options={
                "reduceOptions": {"values": False, "calcs": ["lastNotNull"]},
                "orientation": "auto",
                "textMode": "value_and_name",
                "colorMode": "value",
            },
            field_config={
                "defaults": {
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": 0, "color": "green"},
                            {"value": 1, "color": "yellow"},
                            {"value": 10, "color": "red"},
                        ],
                    }
                }
            },
        ),
    ]

    return GrafanaDashboard(
        title="MegaAgent API Monitoring",
        uid="megaagent-api",
        panels=panels,
        tags=["api", "http", "performance"],
    )


def create_orchestration_dashboard() -> GrafanaDashboard:
    """Create dashboard for orchestration monitoring."""
    panels = [
        # Workflow Executions
        Panel(
            title="Workflow Executions",
            type="graph",
            grid_pos={"x": 0, "y": 0, "w": 12, "h": 8},
            targets=[
                {
                    "expr": "sum(rate(workflow_executions_total[5m])) by (status)",
                    "refId": "A",
                    "legendFormat": "{{status}}",
                }
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "multi"},
            },
        ),
        # Error Recovery Attempts
        Panel(
            title="Error Recovery Attempts",
            type="graph",
            grid_pos={"x": 12, "y": 0, "w": 12, "h": 8},
            targets=[
                {
                    "expr": "sum(rate(workflow_error_recovery_attempts_total[5m])) by (strategy)",
                    "refId": "A",
                    "legendFormat": "{{strategy}}",
                }
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "multi"},
            },
        ),
        # Human Review Queue
        Panel(
            title="Human Reviews Pending",
            type="stat",
            grid_pos={"x": 0, "y": 8, "w": 6, "h": 4},
            targets=[
                {
                    "expr": "workflow_human_reviews_pending",
                    "refId": "A",
                    "legendFormat": "Pending",
                }
            ],
            options={
                "reduceOptions": {"values": False, "calcs": ["lastNotNull"]},
                "orientation": "auto",
                "textMode": "value_and_name",
                "colorMode": "value",
            },
            field_config={
                "defaults": {
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": 0, "color": "green"},
                            {"value": 5, "color": "yellow"},
                            {"value": 20, "color": "red"},
                        ],
                    }
                }
            },
        ),
        # Routing Confidence
        Panel(
            title="Routing Confidence (avg)",
            type="gauge",
            grid_pos={"x": 6, "y": 8, "w": 6, "h": 4},
            targets=[
                {
                    "expr": "avg(workflow_routing_confidence)",
                    "refId": "A",
                    "legendFormat": "Confidence",
                }
            ],
            options={
                "orientation": "auto",
                "showThresholdLabels": False,
                "showThresholdMarkers": True,
            },
            field_config={
                "defaults": {
                    "unit": "percentunit",
                    "min": 0,
                    "max": 1,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {"value": 0, "color": "red"},
                            {"value": 0.75, "color": "yellow"},
                            {"value": 0.9, "color": "green"},
                        ],
                    },
                }
            },
        ),
    ]

    return GrafanaDashboard(
        title="MegaAgent Orchestration",
        uid="megaagent-orchestration",
        panels=panels,
        tags=["orchestration", "workflow", "langgraph"],
    )


def create_system_dashboard() -> GrafanaDashboard:
    """Create dashboard for system-level monitoring."""
    panels = [
        # Database Connections
        Panel(
            title="Database Connections",
            type="graph",
            grid_pos={"x": 0, "y": 0, "w": 12, "h": 8},
            targets=[
                {
                    "expr": "db_connections_active",
                    "refId": "A",
                    "legendFormat": "Active",
                },
                {
                    "expr": "db_connections_idle",
                    "refId": "B",
                    "legendFormat": "Idle",
                },
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "multi"},
            },
        ),
        # Memory Usage
        Panel(
            title="Memory Usage",
            type="graph",
            grid_pos={"x": 12, "y": 0, "w": 12, "h": 8},
            targets=[
                {
                    "expr": "process_resident_memory_bytes",
                    "refId": "A",
                    "legendFormat": "Resident Memory",
                }
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "single"},
            },
            field_config={"defaults": {"unit": "bytes"}},
        ),
        # Vector Store Operations
        Panel(
            title="Vector Store Operations",
            type="graph",
            grid_pos={"x": 0, "y": 8, "w": 12, "h": 8},
            targets=[
                {
                    "expr": "sum(rate(vector_store_operations_total[5m])) by (operation)",
                    "refId": "A",
                    "legendFormat": "{{operation}}",
                }
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "multi"},
            },
        ),
        # LLM Request Rate
        Panel(
            title="LLM Request Rate",
            type="graph",
            grid_pos={"x": 12, "y": 8, "w": 12, "h": 8},
            targets=[
                {
                    "expr": "sum(rate(llm_requests_total[5m])) by (model)",
                    "refId": "A",
                    "legendFormat": "{{model}}",
                }
            ],
            options={
                "legend": {"show": True, "placement": "bottom"},
                "tooltip": {"mode": "multi"},
            },
        ),
    ]

    return GrafanaDashboard(
        title="MegaAgent System Overview",
        uid="megaagent-system",
        panels=panels,
        tags=["system", "overview", "infrastructure"],
    )


def create_dashboards(output_dir: str | Path = "grafana_dashboards") -> list[Path]:
    """
    Create all Grafana dashboards and export to JSON files.

    Args:
        output_dir: Directory to save dashboard JSON files

    Returns:
        List of paths to created dashboard files

    Example:
        >>> files = create_dashboards("./grafana_dashboards")
        >>> print(f"Created {len(files)} dashboards")
        Created 4 dashboards
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dashboards = [
        (create_cache_dashboard(), "cache_dashboard.json"),
        (create_api_dashboard(), "api_dashboard.json"),
        (create_orchestration_dashboard(), "orchestration_dashboard.json"),
        (create_system_dashboard(), "system_dashboard.json"),
    ]

    created_files = []
    for dashboard, filename in dashboards:
        file_path = output_dir / filename
        dashboard.export_json(file_path)
        created_files.append(file_path)

    return created_files


def export_dashboard(dashboard: GrafanaDashboard, output_path: str | Path) -> None:
    """
    Export a single dashboard to JSON file.

    Args:
        dashboard: Dashboard to export
        output_path: Path to save JSON file

    Example:
        >>> dashboard = create_cache_dashboard()
        >>> export_dashboard(dashboard, "my_dashboard.json")
    """
    dashboard.export_json(output_path)
