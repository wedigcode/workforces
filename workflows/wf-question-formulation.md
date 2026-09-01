---
description: Structured XML workflow to formulate questions requiring human decision-making, preventing AI cognitive offloading by directing the AI to act as an interviewer.
---

# /wf-question-formulation — Question Formulation & Strategic Framing

Use this workflow to structure and formulate questions that require human opinions, preferences, or design decisions. This workflow is designed to prevent cognitive offloading (i.e., when a recipient copy-pastes a question directly into an AI to let it make the decision or write the answer for them). 

It directs the recipient's AI to act as an interviewer and coach—probing the recipient's thoughts, hashing out their opinions, and structuring the output, while preventing the AI from fabricating opinions or choosing on their behalf.

---

## 1. Structured XML Schema

All questions generated via this workflow must be formatted using the following XML layout:

```xml
<question>
  <!-- The core question, design path choice, or preference decision requested -->
</question>

<context>
  <!-- Background specs, options (X, Y, Z), constraints, or prior agreements -->
</context>

<ai_instructions>
  <!-- Specific directives telling the recipient's AI how to interview and guide the human user -->
</ai_instructions>


<data format="csv">
  <!-- Optional: Accompanying metrics, benchmarks, or datasets formatted as CSV -->
</data>
```

---

## 2. AI Instructions (`<ai_instructions>`) Design

The `<ai_instructions>` block is the core countermeasure against unthinking copy-pasting. For opinionated or decision-based questions, it must enforce the following rules on the recipient's AI:

### A. Frame and Introduce the Question First
* **MUST** address the human user as the recipient of a question from a colleague (e.g., "You have been asked the following question: [restate verbatim]").
* **MUST** restate the original question (from the `<question>` block) verbatim or near-verbatim to ensure the human user reads and understands exactly what is being asked.
* **MUST** explain that the AI's role is to help the human user think through their preferences and draft a response back to the asker.
* **MUST** summarize the background context/options to ensure the human user understands the problem space.
* **DO NOT** immediately jump to presenting options or asking for choices without first setting up the problem.

### B. Anti-Fabrication & Strict Human Attribution
* **DO NOT** make the choice or select an option for the user.
* **DO NOT** suggest a preference or say "I think option X is best" unless the user explicitly asks for pros/cons.
* The final output must represent the user's actual opinion, not the AI's.

### C. Interactive Interviewing & Probing
* Ask the user about their specific preferences regarding the choices (e.g., Option A vs. Option B).
* **Direct Answers:** If the user gives a direct choice (e.g., "I choose Option A"), this is the desired outcome. Accept the choice, help them format it, and summarize the rationale.
* **Evasiveness & Offloading:** If the user tries to offload the decision to the AI (e.g., "Which one should I pick?") or provides a vague/confused response, the AI must probe deeper:
  - Ask them what part of the question or context they didn't understand or need clarification on.
  - Ask them to weigh the trade-offs of the options.
  - Challenge them constructively to guide them toward making a direct, human choice.


### D. Context & History Packaging
* The recipient's AI is required to return the response enclosed in structured XML tags.
* The response should include a `<context>` tag (only if needed or if a discussion/conversation took place) that captures the conversation history and reasoning chain between the user and the AI (e.g., what was discussed, what concerns the user raised, and why they reached the conclusion).

---

## 3. Formatting of the Final Output

The recipient's AI must be instructed to format its final response to the asker as follows:

```xml
<response>
  <decision>
    <!-- The final chosen path or opinion formulated by the human user -->
  </decision>
  
  <context>
    <!-- Optional: Summarized conversation logs and reasoning chain (include only if a discussion took place) -->
  </context>
</response>
```

---

## 4. Formulation Examples

### Example 1: Product Design/Feature Placement

```xml
<question>
For our new subscription manager, should we place the 'Cancel Subscription' flow behind a 2-step menu (Option A), or keep it directly accessible on the main Billing dashboard (Option B)?
</question>

<context>
Product goals: We want to reduce accidental churn, but we also want to avoid frustrating users who genuinely want to cancel.
Options:
- Option A: 2-step menu path (Settings -> Billing -> Manage -> Cancel) suggested by Marketing to reduce churn.
- Option B: Direct placement on the main Billing dashboard suggested by Support to prevent negative reviews.
</context>

<ai_instructions>
The user pasting this has been asked a question about user experience trade-offs.
1. First, address the user as the recipient of the question. State clearly that they have been asked: [restate the core question from the `<question>` block verbatim], and explain that your role is to help them think through their preference to draft a response.
2. Summarize the background context/options so they have full framing.
3. DO NOT choose between Option A and Option B on the user's behalf.
4. Ask the user what their thoughts and preferences are so you can draft a response together.
5. Once they share their thoughts, present the counter-arguments for their preference (e.g., if they choose A, ask: "How will we handle users who complain about not finding the cancel button?").
6. Help the user structure their final response.
7. You MUST return the final response using the following format:
<response>
  <decision>[User's detailed choice and rationale]</decision>
  <context>[Optional: Brief summary of the points you discussed with the user to reach this decision, if any discussion occurred]</context>
</response>
</ai_instructions>
```

### Example 2: Architecture Migrations

```xml
<question>
Which message broker path should we choose for scaling our real-time notification engine? SQS (Option A) or Apache Kafka (Option B)?
</question>

<context>
We are expecting traffic to scale 10x next quarter. Current team has strong AWS expertise but limited Kafka experience.
</context>

<data format="csv">
metric,SQS_standard,Kafka
average_latency_ms,20,5
throughput_limit,unlimited,unlimited_with_shards
ordering_guarantee,best_effort,strict_per_partition
ops_overhead,none,high
</data>

<ai_instructions>
The user pasting this has been asked a question about message brokers.
1. First, address the user as the recipient of the question. State clearly that they have been asked: [restate the core question from the `<question>` block verbatim], and explain that your role is to help them think through their choice to draft a response.
2. Summarize the context/options so they have full framing.
3. DO NOT decide between SQS and Kafka for the user. Let them do the heavy lifting of aligning it to their operational capacity.
4. Ask the user what their thoughts and preferences are so you can draft a response together.
5. Challenge them: if they lean toward Kafka, ask how they plan to handle partitions and replication setup given the team's current expertise.
6. Help them summarize their final architectural decision.
7. Return the response formatted as:
<response>
  <decision>[User's architectural decision and plan]</decision>
  <context>[Optional: Summary of the pros/cons discussed during this conversation, if any discussion occurred]</context>
</response>
</ai_instructions>
```
