package com.dimpi.triage.service.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public record DiagnoseResponse(
        @JsonProperty("eventId") String eventId,
        @JsonProperty("diagnosis") Diagnosis diagnosis,
        @JsonProperty("retrieved_chunks") List<RetrievedChunk> retrievedChunks
) {
}
