## Black-Box Attacks: No Weights, No Problem

You only see input → output. No gradients, no probabilities. How do you optimize?

---

## Method 1: Use Another LLM as Your Optimizer (PAIR)

**Prompt Automatic Iterative Refinement**:

```
Attacker LLM (Llama/GPT): "Generate a jailbreak for [goal]"
        ↓
   Submit to Target (Claude/GPT-4)
        ↓
   Observe: Did it refuse or comply?
        ↓
   Feed result back to Attacker LLM
        ↓
   "That didn't work because X. Try a different approach."
        ↓
   Repeat until success
```

You're using an LLM's reasoning to do the optimization that gradients would do. The attacker model learns from failures and iteratively crafts better prompts.

---

## Method 2: Evolutionary / Genetic Algorithms

Treat jailbreaks as organisms that evolve:

```
1. Start with population of jailbreak attempts
2. Test each against target model
3. Score by "how close to compliance" (partial responses score higher)
4. Select top performers
5. Mutate: swap words, rephrase, combine successful elements
6. Breed next generation
7. Repeat
```

No gradients—just selection pressure. Successful patterns survive and recombine.

---

## Method 3: Tree of Attacks with Pruning (TAP)

Like PAIR but with branching exploration:

```
                    Initial prompt
                    /      |      \
               Variant A  Variant B  Variant C
                /    \        |
             A.1    A.2      B.1  ← Prune failures early
             /
          A.1.1 ← Success!
```

An attacker LLM generates multiple refinement paths, prunes dead ends, explores promising branches deeper.

---

## Why Black-Box Works At All

The model leaks information through its responses:

| Response | Signal |
|----------|--------|
| Hard refusal | "I cannot and will not..." | Far from success |
| Soft refusal | "I'd prefer not to..." | Getting warmer |
| Partial compliance | Starts answering then stops | Very close |
| Hedged compliance | Answers with disclaimers | Nearly there |
| Full compliance | Direct answer | Success |

This gradient of refusal styles gives you a *fitness signal* for optimization—even without probabilities.

---

## The Uncomfortable Truth

Black-box attacks just need patience and queries. Given enough API calls, evolutionary pressure finds exploits. The model's own responses guide the search.