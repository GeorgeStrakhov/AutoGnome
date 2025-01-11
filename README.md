# AutoGnome Project

A minimal approach to building tiny self-aware digital organisms, inspired by:

1. Braitenberg's Vehicles - Simple units with emergent complex behavior
2. Hofstadter's Strange Loops - Self-reference as basis for consciousness
3. Metzinger's Being No One - Self-model theory of consciousness
4. Conway's Game of Life - Cellular automata
5. Weizenbaum's ELIZA - Proactivity as a basis for perceived intelligence
6. Michael Levin's The Collective Intelligence of Morphogenesis - Collective intelligence building up and negotiating with the constraints
7. Theo Jansen's Strandbeest - Self-propelled autonomous creatures with a guided evolution
8. Karl Sims's Evolved Virtual Creatures - Evolutionary algorithm for creating virtual creatures

Our basic building block for thought is an LLM completion, which represents a single thought-thread. Out of these thought-threads stuck in a loop with time-persistent state, we will try to build a self-aware digital organism. We will go very very slowly, starting really simple and adding complexity over time - just like Braitenberg did with his vehicles.

We will start with a single stupid AutoGnome AG1, who is simply declaring its existence every second (at every turn of the loop).
But the end goal is to build an autonomous digital organism with which can live independently in the datasphere.

Our future AG(n) should be able to:
- run continuously on a server in the cloud
- have a singular state that is changes across time. state will include things like energy level, emotional state etc.
- have persistent memories (both short and long term) that it can use to make decisions about what to do next
- have long-term values and goals that it can use to make decisions about what to do next, while being informed by current context and short-term goals.
- should be able to decide to change its goals and values
- have a way to sense its environment i.e. have multiple sensors that can be used to understand the context and context changes. e.g. if AG(n) receives an email or a message or someone replies to its tweet etc.
- have a way to act on its environment i.e. have multiple actuators that can be used to influence the environment. e.g. if AG(n) decides to tweet or send an email or do research on the internet or browse the web etc.
- have a way to learn from its experiences and use that to improve its decision-making process. Memories and learnings should be stored in a way that allows for retrieval and reuse. (probably in a vector database)



## AutoGnomes (AG) evolution tracking:

_each new generation is a new commit in this repository with the name e.g. "AG1" for the first generation_

 - [x] AG 1: Pulses "I exist" at regular intervals. Minimal self-assertion.
 - [x] AG 2: Has a name and one state variable: energy level. After a pulse, energy level is reduced. When energy level reaches 0, the autognome stops.
 - [x] AG 3: Sensor for monitoring its own energy level and ability to decide to rest or continue. Spending one pulse without saying anything is a rest.
 - [x] AG 4: Simple environmental sensor (light/dark) through checking a file. Develops fear of the dark: rests more frequently in darkness, pulses more in light. First emotional response to environment.
 - [x] AG 5: Short-term memory and basic pattern recognition. Remembers its last few experiences (light/dark transitions) and starts to anticipate changes. Can say things like "The light changed 3 times in the last minute" or "It's been dark for a while now...". Also facial expression changes depending on the emotional state, just for the fun of it.
 - [x] AG 6: Long-term persistent memory (currently jsonl, but in the future will be vector storage)
 - [ ] AG 7: Persistent state across sessions. Stores energy level, emotional state, and other vital stats in a state file. When restarted, it remembers its previous state and continues from there.