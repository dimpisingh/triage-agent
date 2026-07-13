package com.dimpi.triage.service.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

// The Python FastAPI service returns snake_case field names (Pydantic
// default), so each field is mapped explicitly rather than relying on
// Jackson's naming strategy globally, to keep this record self-describing.
public record RetrievedChunk(
        @JsonProperty("chunk_id") String chunkId,
        @JsonProperty("text") String text,
        @JsonProperty("source") String source,
        @JsonProperty("score") double score
) {
}
