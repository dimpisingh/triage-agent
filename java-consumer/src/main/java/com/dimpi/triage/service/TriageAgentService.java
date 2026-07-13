package com.dimpi.triage.service;

import com.dimpi.triage.consumer.BuildFailureEvent;
import com.dimpi.triage.service.dto.DiagnoseResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.util.Optional;

/**
 * Bridges the Kafka consumer (durable, ordered, Java/Spring) to the
 * Python RAG + LangGraph agent (stateless reasoning layer, called over
 * REST). This is the seam in the polyglot architecture described in the
 * project README: Java owns ingestion/durability, Python owns the
 * agentic/RAG ecosystem.
 */
@Service
public class TriageAgentService {

    private static final Logger log = LoggerFactory.getLogger(TriageAgentService.class);

    private final RestClient triageAgentRestClient;
    private final boolean escalateOnError;

    public TriageAgentService(
            RestClient triageAgentRestClient,
            @Value("${triage.agent.escalate-on-error:true}") boolean escalateOnError
    ) {
        this.triageAgentRestClient = triageAgentRestClient;
        this.escalateOnError = escalateOnError;
    }

    /**
     * Calls the Python /diagnose endpoint and handles the result. This is
     * intentionally fail-open: if the agent service is unreachable or
     * errors, we log it as a forced escalation rather than blocking the
     * Kafka consumer thread or triggering endless redelivery, which would
     * stall the partition for every other failure event behind it.
     */
    public Optional<DiagnoseResponse> handleFailure(BuildFailureEvent event) {
        try {
            DiagnoseResponse response = triageAgentRestClient.post()
                    .uri("/diagnose")
                    .contentType(org.springframework.http.MediaType.APPLICATION_JSON)
                    .body(event)
                    .retrieve()
                    .body(DiagnoseResponse.class);

            if (response == null) {
                log.warn("Triage agent returned an empty response for event {}", event.getEventId());
                return Optional.empty();
            }

            logDiagnosis(event, response);
            return Optional.of(response);

        } catch (RestClientException ex) {
            log.error("Triage agent call failed for event {}: {}", event.getEventId(), ex.getMessage());
            if (escalateOnError) {
                log.warn(
                        "Forcing escalation for event {} (repo={}, module={}) because the triage " +
                                "agent could not be reached. This should page/ticket the same as a " +
                                "low-confidence diagnosis.",
                        event.getEventId(), event.getRepo(), event.getAffectedModule()
                );
                // In production: publish to an "escalations" topic / open a
                // ticket here, same downstream path as a low-confidence
                // diagnosis from the agent itself.
            }
            return Optional.empty();
        }
    }

    private void logDiagnosis(BuildFailureEvent event, DiagnoseResponse response) {
        var diagnosis = response.diagnosis();
        if (diagnosis.escalated()) {
            log.warn(
                    "ESCALATED event={} repo={} confidence={} reason={}",
                    event.getEventId(), event.getRepo(), diagnosis.confidence(), diagnosis.escalationReason()
            );
        } else {
            log.info(
                    "DIAGNOSED event={} repo={} rootCause=\"{}\" confidence={} citations={}",
                    event.getEventId(), event.getRepo(), diagnosis.rootCause(),
                    diagnosis.confidence(), diagnosis.citations()
            );
        }
    }
}
