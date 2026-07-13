package com.dimpi.triage.service.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

public record Diagnosis(
        @JsonProperty("root_cause") String rootCause,
        @JsonProperty("proposed_fix") String proposedFix,
        @JsonProperty("confidence") double confidence,
        @JsonProperty("citations") List<String> citations,
        @JsonProperty("escalated") boolean escalated,
        @JsonProperty("escalation_reason") String escalationReason
) {
}
