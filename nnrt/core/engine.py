"""
Engine — Pipeline orchestration.

The engine selects a pipeline, runs passes in order,
manages validation, and packages output.

The engine is NOT where domain logic lives.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from nnrt.core.context import TransformContext, TransformRequest
from nnrt.ir.schema_v0_1 import TransformResult, TransformStatus


# Type alias for a pass function
PassFn = Callable[[TransformContext], TransformContext]


@dataclass
class Pipeline:
    """A named sequence of passes."""

    id: str
    name: str
    passes: list[PassFn]


class Engine:
    """
    Pipeline orchestrator.
    
    Runs passes in order, handles errors, and packages results.
    """

    def __init__(self) -> None:
        self._pipelines: dict[str, Pipeline] = {}

    def register_pipeline(self, pipeline: Pipeline) -> None:
        """Register a pipeline by ID."""
        self._pipelines[pipeline.id] = pipeline

    def list_pipelines(self) -> list[str]:
        """List registered pipeline IDs."""
        return list(self._pipelines.keys())

    def transform(
        self,
        request: TransformRequest,
        pipeline_id: Optional[str] = None,
    ) -> TransformResult:
        """
        Run a transformation.
        
        Args:
            request: The transformation request
            pipeline_id: Which pipeline to use (default: 'default')
            
        Returns:
            TransformResult with IR, trace, and diagnostics
        """
        pipeline_id = pipeline_id or "default"

        if pipeline_id not in self._pipelines:
            # Return error result
            ctx = TransformContext.from_request(request)
            ctx.status = TransformStatus.ERROR
            ctx.add_diagnostic(
                level="error",
                code="PIPELINE_NOT_FOUND",
                message=f"Pipeline '{pipeline_id}' not registered",
                source="engine",
            )
            return ctx.to_result()

        pipeline = self._pipelines[pipeline_id]
        ctx = TransformContext.from_request(request)

        # Run passes in order
        for pass_fn in pipeline.passes:
            try:
                ctx = pass_fn(ctx)
                
                # Check for refusal
                if ctx.status == TransformStatus.REFUSED:
                    ctx.add_trace(
                        pass_name=pass_fn.__name__,
                        action="pipeline_halted",
                    )
                    break
                    
            except Exception as e:
                ctx.status = TransformStatus.ERROR
                ctx.add_diagnostic(
                    level="error",
                    code="PASS_ERROR",
                    message=f"Pass '{pass_fn.__name__}' failed: {e}",
                    source="engine",
                )
                ctx.add_trace(
                    pass_name=pass_fn.__name__,
                    action="error",
                )
                break

        return ctx.to_result()


# Global engine instance
_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Get or create the global engine instance."""
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine


def transform(text: str, pipeline_id: Optional[str] = None) -> TransformResult:
    """
    Convenience function for simple transformations.
    
    Args:
        text: Raw narrative text
        pipeline_id: Which pipeline to use
        
    Returns:
        TransformResult
    """
    engine = get_engine()
    request = TransformRequest(text=text)
    return engine.transform(request, pipeline_id)
