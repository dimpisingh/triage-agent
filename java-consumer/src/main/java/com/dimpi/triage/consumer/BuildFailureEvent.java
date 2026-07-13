package com.dimpi.triage.consumer;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.Instant;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class BuildFailureEvent {

    private String eventId;
    private Instant timestamp;
    private String repo;
    private String branch;
    private String commitSha;
    private String pipelineId;
    private String stage;
    private String failureType;
    private int exitCode;
    private String rawLogExcerpt;
    private String logStorageUrl;
    private String affectedModule;
    private String triggeredBy;
    private int retryCount;

    public BuildFailureEvent() {
    }

    // --- getters / setters ---

    public String getEventId() {
        return eventId;
    }

    public void setEventId(String eventId) {
        this.eventId = eventId;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Instant timestamp) {
        this.timestamp = timestamp;
    }

    public String getRepo() {
        return repo;
    }

    public void setRepo(String repo) {
        this.repo = repo;
    }

    public String getBranch() {
        return branch;
    }

    public void setBranch(String branch) {
        this.branch = branch;
    }

    public String getCommitSha() {
        return commitSha;
    }

    public void setCommitSha(String commitSha) {
        this.commitSha = commitSha;
    }

    public String getPipelineId() {
        return pipelineId;
    }

    public void setPipelineId(String pipelineId) {
        this.pipelineId = pipelineId;
    }

    public String getStage() {
        return stage;
    }

    public void setStage(String stage) {
        this.stage = stage;
    }

    public String getFailureType() {
        return failureType;
    }

    public void setFailureType(String failureType) {
        this.failureType = failureType;
    }

    public int getExitCode() {
        return exitCode;
    }

    public void setExitCode(int exitCode) {
        this.exitCode = exitCode;
    }

    public String getRawLogExcerpt() {
        return rawLogExcerpt;
    }

    public void setRawLogExcerpt(String rawLogExcerpt) {
        this.rawLogExcerpt = rawLogExcerpt;
    }

    public String getLogStorageUrl() {
        return logStorageUrl;
    }

    public void setLogStorageUrl(String logStorageUrl) {
        this.logStorageUrl = logStorageUrl;
    }

    public String getAffectedModule() {
        return affectedModule;
    }

    public void setAffectedModule(String affectedModule) {
        this.affectedModule = affectedModule;
    }

    public String getTriggeredBy() {
        return triggeredBy;
    }

    public void setTriggeredBy(String triggeredBy) {
        this.triggeredBy = triggeredBy;
    }

    public int getRetryCount() {
        return retryCount;
    }

    public void setRetryCount(int retryCount) {
        this.retryCount = retryCount;
    }
}
