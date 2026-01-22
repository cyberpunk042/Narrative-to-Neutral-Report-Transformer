## The tool will have a structured output mode.
Contains probe but also a massive header of extraction and reconstitition.

## It will have a probe output mode.
Contains the neutralized report based of atomic interpretation.

## It will have a raw output mode.
Contains the neutralized report based of atomic interpretation. 
(reduced level of transformation for private version of report vs public version of report)

## It will have a raw structured output mode.
Contains raw but also a massive header of extraction and reconstitition.
(reduced level of transformation for private version of report vs public version of report)

## It will have versions.
Each of them will now be the same pipeline, but with different parameters.
Version will define the level of transformation and output that will live in parallel as the "old" version.
At the start of this refactoring we will have only one version. V1. we will continue V1 till the converage feel strong. V2 will only happen later when we realize potential fundamental flaw that will allow us to reroute parts of the pipeline to a new version.