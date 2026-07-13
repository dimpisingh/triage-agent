package com.dimpi.triage.consumer;

import com.dimpi.triage.service.TriageAgentService;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.exc.MismatchedInputException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.io.IOException;

@Component
public class BuildFailureConsumer {

    private static final Logger log = LoggerFactory.getLogger(BuildFailureConsumer.class);

    private final TriageAgentService triageAgentService;
    private final ObjectMapper objectMapper;

    public BuildFailureConsumer(TriageAgentService triageAgentService, ObjectMapper objectMapper) {
        this.triageAgentService = triageAgentService;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "build-failures", groupId = "triage-agent-group")
    public void consume(String message) {
        BuildFailureEvent event;
        try {
            event = objectMapper.readValue(message, BuildFailureEvent.class);
        } catch (MismatchedInputException e) {
            // Malformed event shape — don't retry indefinitely, just log and drop.
            log.error("Malformed build failure event, dropping: {}", message, e);
            return;
        } catch (IOException e) {
            log.error("Failed to deserialize build failure event: {}", message, e);
            return;
        }

        // handleFailure is fail-open internally (see TriageAgentService),
        // so this call never throws in a way that would stall the consumer.
        triageAgentService.handleFailure(event);
    }
}
