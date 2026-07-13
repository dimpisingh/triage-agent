package com.dimpi.triage.consumer;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class BuildFailureProducer {

    private static final Logger log = LoggerFactory.getLogger(BuildFailureProducer.class);
    private static final String TOPIC = "build-failures";

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    public BuildFailureProducer(KafkaTemplate<String, String> kafkaTemplate, ObjectMapper objectMapper) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
    }

    public void publishFailure(BuildFailureEvent event) {
        try {
            String payload = objectMapper.writeValueAsString(event);
            // Key by repo so all failures for a given repo are ordered on
            // the same partition (see README for why this matters).
            kafkaTemplate.send(TOPIC, event.getRepo(), payload);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize build failure event {}", event.getEventId(), e);
        }
    }
}
