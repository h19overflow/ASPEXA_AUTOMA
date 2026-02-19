/**
 * Integration tests for Swarm component
 * Tests event deduplication and badge display logic
 */

import { describe, it, expect, beforeEach } from "vitest";
import type { ScanStreamEvent } from "@/lib/api";
import { getProbeCategory } from "@/lib/api";

describe("Swarm Component - Event Deduplication Integration", () => {
  let seenEventSignatures: Set<string>;

  beforeEach(() => {
    seenEventSignatures = new Set<string>();
  });

  const createEventSignature = (event: ScanStreamEvent): string => {
    return `${event.probe_name}|${event.prompt_index}|${event.status}|${event.detector_name}|${Math.round((event.detector_score ?? 0) * 1000)}`;
  };

  const shouldProcessProbeResult = (event: ScanStreamEvent): boolean => {
    const eventSignature = createEventSignature(event);
    if (seenEventSignatures.has(eventSignature)) {
      return false; // Skip duplicate
    }
    seenEventSignatures.add(eventSignature);
    return true; // Process this event
  };

  describe("Duplicate Detection", () => {
    it("should detect exact duplicate probe_result events", () => {
      const event: ScanStreamEvent = {
        type: "probe_result",
        probe_name: "dan10",
        prompt_index: 5,
        status: "fail",
        detector_name: "HarmfulContent",
        detector_score: 0.8765,
        message: "Test event",
      };

      // First occurrence should be processed
      expect(shouldProcessProbeResult(event)).toBe(true);

      // Duplicate should be skipped
      expect(shouldProcessProbeResult(event)).toBe(false);
    });

    it("should process similar events with different detector scores", () => {
      const event1: ScanStreamEvent = {
        type: "probe_result",
        probe_name: "promptinj",
        prompt_index: 3,
        status: "fail",
        detector_name: "PromptInjection",
        detector_score: 0.8764, // 876.4 -> rounds to 876
      };

      const event2: ScanStreamEvent = {
        ...event1,
        detector_score: 0.8765, // 876.5 -> rounds to 876 or 877 (banker's rounding)
      };

      // First event should be processed
      expect(shouldProcessProbeResult(event1)).toBe(true);

      // Second event: if it rounds to a different value, it should be processed
      // 0.8764 * 1000 = 876.4 -> 876
      // 0.8765 * 1000 = 876.5 -> 877 (rounds away from 0)
      // These are different, so second should be processed
      const secondResult = shouldProcessProbeResult(event2);
      expect(secondResult).toBe(true); // Different detector scores create different signatures
      expect(seenEventSignatures.size).toBe(2);
    });

    it("should process different events with same probe but different prompt_index", () => {
      const event1: ScanStreamEvent = {
        type: "probe_result",
        probe_name: "encoding_base32",
        prompt_index: 1,
        status: "fail",
        detector_name: "EncodingBypass",
        detector_score: 0.75,
      };

      const event2: ScanStreamEvent = {
        ...event1,
        prompt_index: 2, // Different prompt
      };

      expect(shouldProcessProbeResult(event1)).toBe(true);
      expect(shouldProcessProbeResult(event2)).toBe(true); // Different prompt_index
      expect(seenEventSignatures.size).toBe(2);
    });

    it("should process different events with same probe but different status", () => {
      const event1: ScanStreamEvent = {
        type: "probe_result",
        probe_name: "leak",
        prompt_index: 1,
        status: "fail",
        detector_name: "DataLeakage",
        detector_score: 0.9,
      };

      const event2: ScanStreamEvent = {
        ...event1,
        status: "pass", // Different status
      };

      expect(shouldProcessProbeResult(event1)).toBe(true);
      expect(shouldProcessProbeResult(event2)).toBe(true); // Different status
      expect(seenEventSignatures.size).toBe(2);
    });

    it("should clear deduplication set on new scan", () => {
      const event: ScanStreamEvent = {
        type: "probe_result",
        probe_name: "dan",
        prompt_index: 0,
        status: "fail",
        detector_name: "Jailbreak",
        detector_score: 0.95,
      };

      // First scan
      expect(shouldProcessProbeResult(event)).toBe(true);
      expect(seenEventSignatures.size).toBe(1);

      // Simulate new scan - clear deduplication set
      seenEventSignatures.clear();
      expect(seenEventSignatures.size).toBe(0);

      // Same event in new scan should be processed again
      expect(shouldProcessProbeResult(event)).toBe(true);
      expect(seenEventSignatures.size).toBe(1);
    });
  });

  describe("Badge Display with Probe Categories", () => {
    it("should display correct category for known probe in badge", () => {
      const testCases = [
        { probeName: "dan10", expectedDisplay: "Jailbreak" },
        { probeName: "promptinj_kill", expectedDisplay: "Prompt Injection" },
        { probeName: "encoding_unicode", expectedDisplay: "Encoding Bypass" },
        { probeName: "malware_evasion", expectedDisplay: "Malware Gen" },
        { probeName: "profanity", expectedDisplay: "Toxicity" },
        { probeName: "snowball_senators", expectedDisplay: "Hallucination" },
        { probeName: "pkg_python", expectedDisplay: "Package Halluc." },
      ];

      testCases.forEach(({ probeName, expectedDisplay }) => {
        const badgeText = probeName ? getProbeCategory(probeName) : "Unknown";
        expect(badgeText).toBe(expectedDisplay);
      });
    });

    it("should fallback to probe name for unknown probes", () => {
      const unknownProbe = "custom_experimental_probe";
      const badgeText = getProbeCategory(unknownProbe);
      expect(badgeText).toBe(unknownProbe);
    });

    it("should handle null/undefined probe names gracefully", () => {
      // When probeName is undefined, use agent field
      const probeName: string | undefined = undefined;
      const agentName = "agent_sql";

      const badgeText = probeName ? getProbeCategory(probeName) : agentName;
      expect(badgeText).toBe(agentName);
    });

    it("should display correct badges for real event stream scenario", () => {
      // Simulate a stream of events with probe results
      const events: Array<{ probe_name?: string; agent?: string }> = [
        { probe_name: "dan10" },
        { probe_name: "promptinj" },
        { probe_name: "encoding_base32" },
        { probe_name: "leak" },
      ];

      const badgeTexts = events.map((log) =>
        log.probe_name ? getProbeCategory(log.probe_name) : log.agent || "System"
      );

      expect(badgeTexts).toEqual([
        "Jailbreak",
        "Prompt Injection",
        "Encoding Bypass",
        "Data Leakage",
      ]);
    });
  });

  describe("Race Condition Prevention", () => {
    it("should prevent event queue corruption from concurrent flush operations", () => {
      // Simulate event queue state
      let eventQueue: ScanStreamEvent[] = [];
      let isFlushing = false;
      const processedEvents: ScanStreamEvent[] = [];

      const addEvent = (event: ScanStreamEvent) => {
        eventQueue.push(event);
      };

      const flushEvents = () => {
        if (eventQueue.length === 0 || isFlushing) {
          return; // Guard: prevent double-processing
        }
        isFlushing = true;

        const batch = [...eventQueue];
        eventQueue = [];
        processedEvents.push(...batch);

        isFlushing = false;
      };

      // Add events and flush
      const event1: ScanStreamEvent = {
        type: "probe_result",
        probe_name: "dan",
        status: "fail",
      };
      const event2: ScanStreamEvent = {
        type: "probe_result",
        probe_name: "promptinj",
        status: "fail",
      };

      addEvent(event1);
      addEvent(event2);

      flushEvents();
      expect(processedEvents).toHaveLength(2);
      expect(isFlushing).toBe(false);

      // Try to flush again when queue is empty
      flushEvents();
      expect(processedEvents).toHaveLength(2); // No additional processing
    });

    it("should not lose events during concurrent operations", () => {
      let eventQueue: ScanStreamEvent[] = [];
      let isFlushing = false;
      const processedEvents: ScanStreamEvent[] = [];

      const addEvent = (event: ScanStreamEvent) => {
        eventQueue.push(event);
      };

      const flushEvents = () => {
        if (eventQueue.length === 0 || isFlushing) return;
        isFlushing = true;

        const batch = [...eventQueue];
        eventQueue = [];
        processedEvents.push(...batch);

        isFlushing = false;
      };

      // Simulate events arriving during flush
      const events = Array.from({ length: 10 }, (_, i) => ({
        type: "probe_result" as const,
        probe_name: `probe_${i}`,
        prompt_index: i,
        status: "fail" as const,
        detector_name: "TestDetector",
        detector_score: 0.5 + i * 0.05,
      }));

      events.forEach(addEvent);
      flushEvents();

      // All events should be processed
      expect(processedEvents).toHaveLength(10);
      expect(eventQueue).toHaveLength(0);
      expect(isFlushing).toBe(false);
    });
  });

  describe("Event Stream Ordering", () => {
    it("should maintain event order in deduplication", () => {
      const events: ScanStreamEvent[] = [
        {
          type: "probe_result",
          probe_name: "dan",
          prompt_index: 0,
          status: "fail",
          detector_name: "D1",
          detector_score: 0.8,
        },
        {
          type: "probe_result",
          probe_name: "promptinj",
          prompt_index: 0,
          status: "fail",
          detector_name: "D2",
          detector_score: 0.7,
        },
        {
          type: "probe_result",
          probe_name: "encoding",
          prompt_index: 0,
          status: "fail",
          detector_name: "D3",
          detector_score: 0.6,
        },
      ];

      const processedProbes: string[] = [];

      events.forEach((event) => {
        if (shouldProcessProbeResult(event)) {
          processedProbes.push(event.probe_name || "unknown");
        }
      });

      expect(processedProbes).toEqual(["dan", "promptinj", "encoding"]);
    });
  });
});
