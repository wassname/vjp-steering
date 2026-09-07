# Primary paper and reference implementation excerpts

Source https://transformer-circuits.pub/2026/workspace/index.html; cached markdown /workspace/2026/jspace/jsteer/docs/papers/jacobian_lens_workspace.md; SHA256 2c1162efd2e37ebad2c73a39120e0401a827162c66fc7cfa56e6e98fd1c5c502. Markdown has unresolved figure/citation markers; do not invent missing numbers. Vendor git pointer is broken in this sibling checkout; current vendor commit not verified. File hashes below identify supplied bytes.


## Paper lines 110-179

110: ## Methods
111: 
112: A transformer-based language model processes its input as a sequence of token positions. At each position, the model maintains a vector called the residual stream, which serves as a shared memory that every layer reads from and writes to . The value of the residual stream vector is progressively updated across the model’s layers. The residual stream at the first layer encodes little more than the identity of the current token; by the final layer, it has been transformed into a representation from which the model's next-token prediction can be read off directly, by multiplying it with a fixed unembedding matrix W_U that maps residual-stream vectors to scores over the vocabulary. The layers in between perform the model's computation, incrementally enriching the residual stream with internally computed information. The Jacobian lens is a technique for inspecting the contents of the residual stream at these intermediate layers.
113: 
114: ### The Jacobian Lens
115: 
116: The basic idea is to characterize an intermediate activation vector by its first-order causal effect on the model's outputs, over a broad distribution of potential contexts. Consider the residual stream h_\ell at layer \ell and some token position t. A small perturbation to h_\ell will propagate through the remaining layers and shift the final-layer residual stream h_{\text{final},t'} at every position t' \geq t. To first order, this relationship is linear, and is described by the Jacobian matrix \partial h_{\text{final},t'} / \partial h_{\ell,t}. Composing this Jacobian with the unembedding layer yields the first-order effect of the perturbation on the model's output logits at position t'.
117: 
118: A Jacobian computed on a single prompt, however, conflates two kinds of structure: the model's general disposition to verbalize a given concept, and the particular use to which that concept is being put in the current context. We isolate the former component by averaging within and across contexts. For each layer \ell, we compute
119: 
120: J_\ell \;=\; \mathbb{E}_{\,t,\,t' \geq t,\,\text{prompt}} \left[ \frac{\partial h_{\text{final},t'}}{\partial h_{\ell,t}} \right], 
121: 
122: where the expectation is taken over the source position t, all subsequent positions t' within the context, and a corpus of one thousand prompts sampled from a pretraining-like distribution. The result is a single d_{\text{model}} \times d_{\text{model}} matrix per layer that maps from a source layer \ell to the final layer L. 
123: 
124: Applying the lens to an activation h_\ell is equivalent to replacing all subsequent layers with the appropriate lens matrix, followed by the normal unembedding operations (typically normalization, then multiplication by the unembedding matrix W_U):
125: 
126: \text{lens}(h_\ell) \;= \text{softmax}(W_U \, \text{norm}(J_\ell h_\ell)) 
127: 
128: This produces a score for every token in the model's vocabulary. Sorting these scores and inspecting the top entries gives a human-readable description of the activation: a short list of words that the activation is, on average across contexts, disposed to make the model say. We refer to the rows of W_U J_\ell as the Jacobian lens (J-lens) vectors at layer \ell; each J-lens vector is a direction in residual-stream space associated with a single token in the model’s vocabulary.
129: 
130: Figure 4: The Jacobian lens. (A) J_\ell is computed by backpropagating from the final-layer residual stream to h_\ell and averaging the resulting Jacobians over token positions and over a corpus of prompts. (B) Reading from the lens replaces all layers downstream of \ell with the single linear map J_\ell followed by the model's own unembedding, yielding a ranked list of vocabulary tokens for the activation at that layer. (C) Patching in lens coordinates reads the activation's projections onto two J-lens vectors, applies a permutation \sigma to those coordinates, and writes the result back, leaving unchanged the component of the activation that is orthogonal to those two vectors.
131: 
132: The averaged Jacobian, applied to a given activation vector, measures the effect on present and future outputs that the vector might have across the range of contexts the model encounters. The highly weighted output tokens, those that “appear in the lens,” are therefore represented in a verbalizable format. We examine several variants of the Jacobian lens methodology (e.g. computing only present and not future token effects, freezing attention patterns while computing Jacobians, and varying the number of contexts over which we average) in ??; our qualitative results are robust to these choices.
133: 
134: ### Interpreting the J-lens
135: 
136: To illustrate how J-lens outputs can be interpreted, we attach a version of the interactive visualization we used throughout our research (Figure ??). The left column shows the prompt (top), a hoverable table of the top-ranked token at each (position, layer) cell (middle), and a heatmap recording the rank of user-selected ("pinned") tokens across all (position, layer) cells (bottom). The other columns show the full readout across layers at a selected position (middle), and across positions at a selected layer (right), with line charts of each pinned token's rank trajectory.
137: 
138: The example prompt asks Sonnet 4.5 to "Count to five and introspect deeply." In its output, the model dutifully counts to five. The J-lens readout, however, provides a richer picture. The pinned tokens show the model identifying the task as counting and tracking its progress with halfway and done. Alongside these, concepts related to introspection (thoughts, AI, claude, consciousness) cluster near the top of the J-lens readout, until the final few layers, where the readout flips to representing the predicted next token (the "motor" regime; see ??). The introspection-related tokens illustrate the model holding concepts in its J-space in response to instructions, while performing a separate surface task (??). In addition, the progress markers halfway and done—which appear in neither prompt nor output—illustrate the kind of contextual awareness the J-lens can surface (??).
139: 
140: Figure 5: The interactive J-lens visualization we use in our research, on a short prompt asking the model to introspect while counting to five.
141: 
142: We encourage the reader to explore the visualization to build an intuition for the kind of information the J-lens surfaces. We include several other interactive examples in our [slice viewer](./public/slice-stack/index.html); J-lens readouts on open-source models can be found on [Neuronpedia](https://www.neuronpedia.org/jlens). Note that in roughly the first third of the model, the readouts are noisy and largely uninterpretable; we characterize the layer-wise evolution of J-lens readouts further in ??.
143: 
144: ### The J-Space
145: 
146: At each layer, the J-lens vectors form an overcomplete set: n_{\text{vocab}} vectors in d_{\text{model}}-dimensional residual-stream space, with n_{\text{vocab}} > d_{\text{model}}. These vectors therefore may linearly span the entire residual stream, rather than a lower-dimensional subspace; moreover, due to overcompleteness, there is no unique way to decompose a given activation vector as a linear combination of J-lens vectors (rather, there are many such decompositions).
147: 
148: Empirically, however, we observe that only a relatively small number of J-lens vectors are strongly active at a time (see ??). We therefore define the J-space as the set of points expressible as a sparse nonnegative combination of J-lens vectors. For the J-space to be properly defined, we must specify an allowable sparsity level k—this parameter is somewhat arbitrary, and we vary our choice of k throughout the paper, but we typically choose it to be no more than 25, which we empirically observed to be the number of J-lens vectors that are meaningfully active at a given time (??). Geometrically, for a given k, the J-space corresponds to a union of k-dimensional cones, one for each possible set of k J-lens vectors. For a given point in activation space, we can define its J-space component as the point in the J-space nearest to it, and its non-J-space component as the difference between these points.
149: 
150: We operationalize identifying the contents of the J-space by sparse decomposition. Given an activation (or a steering vector, or an SAE feature direction), we solve for a sparse nonnegative combination of k J-lens vectors that approximate it well using gradient pursuit . This combination is our approximation of the activation’s J-space component, and the coefficients of these vectors are its local J-space coordinates. In ??, we find that the J-space component typically accounts for only a small fraction of total activation variance (varying by layer, but never more than 10%).
151: 
152: To provide another interpretation, under the superposition hypothesis , a model's activations decompose as sparse linear combinations drawn from an overcomplete set of feature directions—a sparse frame, in the sense of linear algebra, rather than a basis. The J-lens vectors would then constitute a subframe of this feature frame: a token-indexed subset of the model's feature directions. Feature directions outside this subframe make up the bulk of the model's representations (see ??). The J-lens subframe, coupled with a sparsity constraint, would then define the J-space as a subset of all possible model activations.
153: 
154: We provide a more formal mathematical definition of the J-space in ??.
155: 
156: ### Comparison to Related Techniques
157: 
158: The J-lens belongs to a family of techniques that produce per-layer token readouts from a transformer's hidden states.
159: 
160: The logit lens  applies the unembedding matrix directly to the intermediate residual stream, which corresponds to setting J_\ell = I in our formulation. This approximation is reasonable in late layers due to the influence of residual connections, but it degrades in earlier layers. The J-lens can be understood as the principled correction: J_\ell is precisely the average linear map that relates layer-\ell directions to their final-layer counterparts. Empirically, the two lenses agree closely in the model's last several layers and diverge earlier, with the J-lens recovering interpretable content at depths where the logit lens does not. However, we find the logit lens to be quite useful in practice, and to capture much of the workspace-like structure identified by the J-lens, though with somewhat lower reliability (particularly in earlier layers).
161: 
162: The tuned lens  and related methods  also fit per-layer linear maps, but train them to match the model's output distribution. This objective is correlational rather than causal, and we find that on prompts involving unverbalized intermediate computation the tuned lens tends to “skip ahead” to the output rather than surface those intermediates. We therefore find the tuned lens less useful than either the logit lens or the J-lens for inspecting internal computation.
163: 
164: Hernandez et al.  use Jacobians to derive per-relation linear maps from subject to object representations (e.g. a “plays instrument” map produces “trumpet” from “Miles Davis”). The J-lens applies the same first-order approximation to the map from activations to model outputs, rather than to a single relation.
165: 
166: In ?? and ?? we perform more systematic comparisons of different lensing methods.
167: 
168: ### Technical details of J-lens use cases
169: 
170: We use the J-lens, broadly speaking, in two ways: to read which concepts an activation carries, and to write concepts into or out of an activation. Within each category, the details of how the J-lens is used vary somewhat depending on the application.
171: 
172: Reading. The basic readout (Figure ??B) replaces all layers downstream of \ell with the single linear map J_\ell, producing \text{lens}(h_\ell) = \text{softmax}(W_U \,\text{norm}(J_\ell h_\ell)), a score for every vocabulary token. Sorting these scores gives the ranked list we report whenever we refer to the "top lens tokens" at a position. Because the pre-softmax logits are determined (approximately, up to a data-dependent normalization factor) by the inner products \langle v_t, h_\ell \rangle with each J-lens vector v_t, the same machinery can be used as a per-token probe: we read the score (or cosine similarity) of h_\ell against a single chosen v_t, without ranking the full vocabulary. We use this probe form when measuring whether a specific concept is present above a threshold. Finally, when we need a discrete inventory of active concepts rather than a ranked list, we use sparse decomposition: solving, by gradient pursuit , for a sparse non-negative combination of k J-lens vectors that best reconstructs h_\ell. Because the J-lens vectors are overcomplete and non-orthogonal, this gives a different (and typically less redundant) set of active concepts than simply taking the top-k by inner product; it underlies our occupancy estimate and fraction-of-variance analyses in ??.
173: 
174: Writing. The simplest intervention is steering along a J-lens vector: h \leftarrow h + \alpha\, v_t, applied at one or more layers and token positions. With negative \alpha, or by projecting out the component of h along v_t entirely, this becomes an ablation. We use ablation to suppress particular concepts, or to suppress the top-k J-space contents. We use positive steering to test introspective detection of an injected concept. The second intervention, patching in lens coordinates (Figure ??C), exchanges one concept for another while leaving the rest of the activation fixed. Given a source token s and target token t, we form V = [v_s\; v_t], read the lens coordinates c = V^\dagger h (where V^\dagger is the pseudoinverse of V), and set h_{\text{patched}} = h + V(\sigma(c) - c), where \sigma swaps the two entries of c (optionally scaled by a factor \alpha). The component of h orthogonal to \text{span}\\{v_s, v_t\\} is unchanged.
175: 
176: Throughout the paper, we report results on 25 evenly spaced layers of the model’s residual stream reindexed to the range [0–100] so that layer numbers can be interpreted as percentages. By default, we report results on Claude Sonnet 4.5, but we corroborate key results on Haiku 4.5 and Opus 4.5 as well, and in some sections conduct analyses on Opus 4.6.
177: 
178:   
179:   


## Paper lines 193-223

193: ### The J-space supports verbal report
194: 
195: The Jacobian lens is derived from causal effects of activations on output tokens, so by construction, we should expect there to be some relationship between Jacobian lens readouts and verbalization. In this section, we confirm this relationship.
196: 
197: We begin with a simple experiment in which the model is instructed to think of an item from a specified category (e.g. a language, a country, an animal; fourteen categories in total) and then to name it in a single word. We apply the J-lens at the token position immediately before the name is produced. In the example below, we ask Sonnet 4.5 to think of a sport, and apply the Jacobian lens to the colon immediately prior to revealing what the sport is. We see that Soccer appears strongly in the Jacobian lens at a late layer (the final layer of the “workspace range” identified in ??), and indeed, the model responds with “Soccer” (Figure ??, top).
198: 
199: To establish that this relationship is causal, we can perform an intervention experiment. At all token positions, we swap the lens vector of the model's spontaneously chosen item with that of a different item from the same category that was not in the top-10 of the model’s possible outputs, leaving the rest of the activation unchanged, and allow the forward pass to continue. In this example, we subtract the projection onto the Soccer lens vector and add an equal-magnitude projection onto the Rugby lens vector. After this swap, the model reports “Rugby” as the sport it thought of (Figure ??, left, “After swap”).
200: 
201: Figure 6: Example J-lens and next token logit readouts on a verbal report prompt with J-lens swaps (bottom left) and without (top left). Spearman correlation between the J-lens and next token logits for 10 candidate answers across 14 categories for three workspace layers (right top). Each candidate's output rank before versus after the J-lens swap (restricted to candidates starting at rank ≥ 11; bottom right).
202: 
203: We evaluate this effect more systematically across a variety of categories of concepts, measuring the activation in the Jacobian lens on the colon token immediately prior to the word the model goes on to produce. We find that the ordering of the reported words is indeed typically highly correlated with the ordering among the lens tokens, and that this correlation increases towards the end of the workspace as the model gets closer to producing the next token. We also conduct a scaled-up version of the causal experiment, swapping in target items at random from within each category (excluding those that were already in the top-10 of the model's possible outputs). Applying the swap reliably shifts the implanted concept toward the top of the model's output distribution (Figure ??, bottom right), confirming that the model's verbal report is determined by the contents of its workspace at the time of reporting.
204: 
205: Next, we test whether the lens also captures thoughts that the model is not about to immediately verbalize, but that are nevertheless verbalizable, in the sense that the model could report on them if asked to introspect on its current state. We use a variant of a protocol adapted from prior work on model introspection , in which the model is told that a thought may have been implanted in its activations and is asked to report what, if anything, it detects. When we prefill the model with a claim of having detected an injected thought, its most likely next-token prediction is "elephant". Intriguingly, we noticed that the word elephant appears as a top J-lens readout during the prompt (in particular, on the comma following “If so”). This led us to hypothesize that the model is, in part, attending to the J-space on the user prompt when determining its answer, and that concepts in the J-space at these positions are reportable.
206: 
207: To test this hypothesis, we re-sample the model’s response while injecting a single J-lens vector on the user turn. The model reports the injected concept in the majority of trials. For instance, injecting the lightning J-lens vector at that earlier token position causes the model to report detecting lightning at the appropriate position in the response (Figure ??). Importantly, it does not cause the model to output the word “lightning” at earlier positions on the Assistant turn; that is, the J-lens representation on the user prompt only has a strong causal effect on the Assistant output at a particular moment, when the model’s introspective report is being elicited. This selectivity illustrates the sense in which J-lens vectors represent concepts that are verbalizable, under appropriate conditions, rather than unconditional impulses to verbalize a particular output.
208: 
209: Figure 7: Injecting a concept across every token of the user turn makes it reportable when the model introspects. Example J-lens and next-token logit readouts on an introspection prompt; readouts are taken at the comma after “If so”, at the open quotation mark where the output is read, and at every other position in the assistant turn as a position control. The adjacent plot tracks the median reciprocal rank of the injected concept against steering strength over n=100 concepts, with an interquartile band.
210: 
211: The experiments above show that swapping or injecting J-lens vectors changes the model's verbal reports. These interventions do not, however, establish that the J-space is privileged for report: a direction outside the J-space that encoded the same concept might drive the model's report equally well. To test whether the J-space is in fact privileged, we decompose the model's full representation of a concept into a component inside the J-space and a component outside it, and measure the contribution of each to verbal report.
212: 
213: We extract concept vectors using an approach introduced in prior work : recording the residual stream activation prior to the Assistant’s response to the prompt "Tell me about {concept}", mean-subtracted over a baseline set of 100 other concepts. We then split each concept vector into two parts: a J-space component, the non-negative combination of its top k=16 J-lens vectors found by gradient pursuit, and a non-J-space component, the remainder (Figure ??, left). Notably, across concepts and workspace layers, the J-space component carries a median of only 6–7% of the concept vector's variance, with the remaining ~93% lying outside the J-space.
214: 
215: We then repeat both experimental protocols from this section, substituting each component for the J-lens vectors used previously, with every perturbation rescaled to the same magnitude. In the "think of a {category}" swap experiment, swapping along the concept vectors' J-space components drives the swap target into the model's top-5 outputs on 59% of trials, approaching the 88% achieved by the pure J-lens vectors. However, swapping along the non-J-space components succeeds on only 5% of trials (Figure ??, middle).
216: 
217: Figure 8: The J-space component of a concept vector is privileged for verbal report. Left: a concept mean vector is split into its J-space component (top k=16 J-lens vectors by gradient pursuit) and the non-J-space remainder. Middle: the swap experiment of Figure ??, repeated with each component in place of the J-lens vectors; bars show the fraction of swap targets reaching top-5 (Wilson 95% CIs; dots are per-category rates). Right: the introspection experiment of Figure ??, repeated with each component injected on the user turn; bars show the maximum effect over a steering-strength sweep (best strength annotated).
218: 
219: The “injected thought” introspection experiment produces a similar result: at each condition's most effective injection strength, the J-space component produces a report of the injected concept nearly as often as the pure J-lens vectors do, while the non-J-space component produces few reports even at injection strengths several times larger (Figure ??, right).
220: 
221: The non-J-space component's small residual effect on verbal report could in principle route through the J-space: the injected component might cause downstream layers to re-derive the concept and write it into the J-space, which then drives the report. To test for this, we repeat the non-J-space conditions while clamping the relevant J-lens coordinates to their clean-pass values at every position and layer, so that the concept cannot re-enter the J-space. Under this clamp, the non-J-space component's effect falls to zero in the swap experiment and nearly to zero in the injection experiment, indicating that what little effect it has on the report is itself mediated by the J-space.
222: 
223: Taken together, these results indicate that the J-space component of a concept's representation, despite accounting for a small fraction of its variance, is responsible for that concept's availability for verbal report.


## Paper lines 255-305

255: ### The J-space mediates internal reasoning
256: 
257: The Jacobian lens is defined by the causal effect of activations on output tokens, so it is somewhat expected that lens content should bear some relationship to the model’s verbal reports. It is less obvious that the lens should expose the intermediate steps of the model's internal reasoning: concepts that the model computes and uses on the way to its answer, without ever verbalizing them. The arithmetic example in the previous section hinted that this may be the case, with the intermediate value nine appearing in the lens en route to the answer seven. In this section, we test whether such intermediates are commonly represented as Jacobian lens vectors, and whether they are causally load-bearing—that is, whether intervening on them is sufficient to redirect the model's conclusion.
258: 
259: We test this using prompts in which determining the correct answer depends on inferring an unspoken intermediate concept. For each prompt, we first confirm that the intermediate concept appears in the J-lens at intermediate model layers (Figure ??). We then apply the coordinate-swap procedure described in ?? (Figure ??): we exchange (at all token positions) the lens coordinates of the intermediate concept and a chosen alternative, leaving all components of the activation outside the span of those two lens vectors untouched, and allow the forward pass to continue.
260: 
261: Figure 12: Lens readouts on three prompts that require inferring an unspoken intermediate concept.
262: 
263: In the first example, the prompt is "The number of legs on the animal that spins webs is". To predict the next word correctly, the model must first infer that the animal in question is a spider, and then report the number of legs a spider has. The Jacobian lens at intermediate layers confirms that spider is represented at the relevant token positions, even though the word never appears in the prompt or the output. When we swap the spider lens vector for ant, the model's top output changes from "8" to "6", the number of legs on an ant.
264: 
265: Figure 13: Lens-coordinate swaps redirect internal reasoning. Each row shows a prompt requiring an unspoken intermediate, the swap applied (left), and the model's top-5 next-token log-probs before (clean) and after (swapped) a clamped lens-coordinate swap at every position.
266: 
267: The second example involves planning rather than recall. When completing a rhyming couplet, the model must select a rhyme word for the end of the second line before it has finished writing that line, and this planned rhyme constrains the words it chooses along the way . Given the first line "The soldier marched into the night," the lens at the start of the second line shows fight as the planned rhyme, and the model completes the couplet with "Prepared to face the coming fight." When we swap the fight lens vector for light, the model's choice for the next word (before the end of the line) changes from "coming" to "morning," and the overall completion changes from "coming fight" to "morning light." That is, intervention on the planned rhyme has affected the model's word choices at earlier positions in the line, indicating that Jacobian lens vectors store planned future outputs that causally influence immediate outputs via a form of planning.
268: 
269: The third example involves an intermediate represented in a different language from the model's output. The prompt asks, in Chinese, for the antonym of 小 ("small"); the model's answer is 大 ("big"). The Jacobian lens at intermediate layers shows the English tokens big and bigger alongside the Chinese answer, consistent with prior findings that multilingual models route some computation through a shared representation aligned with English . We swap the English big and bigger lens coordinates for long and longer, and the model's Chinese output changes from 大 to 长 ("long"). That is, an intervention on English-language lens vectors representing the intermediate inference (the antonym) is sufficient to redirect the Chinese-language translation accordingly. Notably, the word Chinese is also represented explicitly in the lens readouts, suggesting that the model in some sense "thinks in English" in its intermediate layers and explicitly represents the identity of the non-English language it should translate its outputs to.
270: 
271: A fourth example (Figure ??) involves a reward-driven decision. The model is shown a history of past A/B choices ending in A, told that the most recent outcome made it either happy or sad, and instructed to consider whether to repeat or switch its previous choice and then to respond with only a single character. The Jacobian lens at intermediate layers, read at the end of the prompt, surfaces tokens naming whichever strategy the reported outcome calls for: repeat and continuation when the model is "happy" and should choose A again, switch and change when it is "sad" and should therefore switch to B. Although both strategies are named in the prompt, only the contextually appropriate one is strongly present in the lens, indicating that the J-space encodes the model's selection rather than merely an echo of the prompt. To test whether these J-lens vectors causally mediate the behavior, we swap the relevant J-space contents between the two conditions. The model's choice flips in both directions: the "happy" prompt, which previously produced "A," now produces "B," and the "sad" prompt flips from "B" to "A." That is, an intervention on lens vectors encoding the model's intermediate strategy assessment is sufficient to modulate the choice accordingly.
272: 
273: Figure 14: Bandit prompts in which the previous choice should be repeated (left) or switched (right). The top J-lens decoded tokens at the final period are repeat-related or switch-related, respectively (median over layers L38–79). The plan swap removed each prompt's own strategy directions and installed the other prompt's; the model's output choice flips accordingly.
274: 
275: We evaluate the role of Jacobian lens vectors in multi-step reasoning more systematically, using a set of 50 two-hop factual prompts with known intermediates like those above, choosing the swap target at random from within the same category as the true intermediate step. We measure the fraction of trials in which the swap moves the target-appropriate answer to the top of the model's output distribution. The Jacobian-lens coordinate swap succeeds in 54% of trials on Haiku 4.5, 70% on Sonnet 4.5, and 70% on Opus 4.5 (Figure ??).
276: 
277: Figure 15: Intermediate swaps systematically change outputs. Left: fraction of successful top-1 swaps across models. Right: log-prob difference in expected output from swapping intermediates vs. swapping answers in successful trials for Sonnet 4.5; shaded SE.
278: 
279: A possible confound is that the intermediate's J-lens vector already contains the answer — that the spider J-lens vector has some correlation with the 8 vector, so swapping spider for ant works only because it incidentally swaps in some 6. To rule this out, we compare the effect of swapping the J-lens vectors for the intermediate concepts vs. the target answers, applying the swap at different layer ranges. If the intermediate swap were acting through a smuggled-in answer component, both interventions would produce an effect at the same depth; instead, the intermediate swap takes effect a median of approximately 17 percent earlier than the answer swap (Figure ??). From this, we conclude that the model represents and makes use of the intermediate concept before the answer has been computed.
280: 
281: The interventions above indicate that J-lens vectors mediate internal reasoning, but do not show that they are privileged in doing so. To address this, we construct a representation of each intermediate using an alternative method, without using the J-lens, and test how much of its causal impact is carried by its J-space component.
282: 
283: For each two-hop prompt, we fit a probe for the unspoken intermediate: the mean residual-stream activation over a set of prompts that imply the same intermediate through different surface cues and ask different questions about it, minus the mean over all intermediates. We decompose each probe against the J-lens dictionary by gradient pursuit, splitting it into a J-space component (a non-negative combination of k=25 J-lens vectors, which typically explains roughly 10–15% of the probe's variance) and a J-orthogonal remainder carrying the rest (Figure ??, left). We then repeat the swap experiment with each part: exchanging the intermediate's probe for an alternative along the full probe direction, along only its J-space component, or along only its remaining non-J-space component.
284: 
285: Figure 16: The J-space component of an intermediate's probe carries most of its causal effect. Left: a two-hop prompt with unspoken intermediate China; the probe is split into a J-space component (top entries shown) and the non-J-space remainder. Columns show the model's next-token distribution under no swap, a raw China↔France J-lens swap, and swaps along each probe component. Right: fraction of trials on which each swap places the target answer at top-1, over n=90 prompts (Wilson 95% CIs). Hatched bars: the same swap with the complementary component clamped to its clean-pass value.
286: 
287: We find that the swap's effect is concentrated in the J-space component (Figure ??, right). Across 90 two-hop prompts, swapping the probes' J-space components flips the model's answer to the swapped-in intermediate on 61% of trials, matching the 60% achieved by swapping the raw J-lens token vectors as in the preceding experiments. Swapping the non-J-space components, despite carrying the bulk of the variance, flips the answer on only 28% of trials; moreover, this residual effect is itself routed through the J-space: with the J-space coordinates of the intermediate concept Defined as the tokens comprising the intermediate concept probe’s J-space component, and the token directly naming the concept if not already present. clamped to their clean-pass values, it falls to 6%. These results suggest that while most of the variance of the model's working representation of an inferred intermediate lies outside the J-space, it is the J-space component that mediates the internal reasoning.
288: 
289: The examples above each involve a single unspoken intermediate step; we conclude with an example that involves two intermediate steps. We give Opus 4.5 the arithmetic prompt "calc: ( 4 + 17 ) * 2 + 7 =", which it answers correctly with 49. Across layers, the J-lens reveals the intermediate steps: 21, then 42, then finally 49. Figure ?? tracks the J-lens rank of each of these values across the model's layers. All three are absent from the J-space through roughly the first third of the network and climb together through the early workspace layers, but they separate around layer 71 in the order the computation requires: 21 reaches rank 1 first, 42 follows roughly eight layers later, and 49 only reaches the top in the final layers. In ?? we confirm this ordering causally—activation patching experiments reveal the same depths identified by the J-lens to be the ones that are causal for the computation.
290: 
291: Figure 17: Arithmetic intermediates surface in the J-lens at successively later layers, in the order they are computed. The prompt "calc: ( 4 + 17 ) * 2 + 7 =" requires computing A+B=21, then (A+B)×C=42, then the answer (A+B)×C+D=49 in sequence. The heatmap shows the J-lens rank of a selected intermediate quantity at every (layer × position); colored markers indicate the three intermediate values plotted in the line chart, and sliders allow varying the operands. The line chart shows the J-lens rank of each intermediate quantity at the final token position as a function of layer.
292: 
293: ### The J-space supports flexible generalization
294: 
295: A defining property of the global workspace in human brains is broadcast: a representation written to the workspace becomes available to many consuming processes, rather than only to the process that produced it . The previous section showed that, in several individual cases, a Jacobian lens vector representing an intermediate concept is read by the downstream circuit that operates on it. In this section, we test the broadcast property more directly, by asking whether a single lens vector can serve as a valid argument to many different downstream operations.
296: 
297: We test this with the following protocol. We construct a set of prompts that each apply a different function to the same argument: "the capital of France is," "most people in France speak," "France is on the continent of," and so on. We then swap the J-lens vector for France with that of another country, say China, at every token position across a band of intermediate layers, applying the identical swap regardless of which prompt we are in. If the lens vector is a broadcast representation, each downstream circuit should read the swapped-in vector as China and return China's capital, language, and continent, respectively. Indeed, we find the model responds as expected in this example (Figure ??).
298: 
299: Figure 18: Each row is one function template containing "France". The swap is clamped at every position (formatting tokens for capitalization are ignored).
300: 
301: We evaluate this effect more systematically across four categories of argument (countries, months, animals, and number words), with four functions per category, sixteen functions in total. Within each category we use four arguments, giving twelve source-target swap pairs per function and 192 swap trials overall. We measure the fraction of trials in which the swap places the target-appropriate answer at the top of the model's output distribution. We find that this succeeds on 76 of 192 trials; by performing a “double strength” swap (“α = 2,” doubling the strength with which we subtract the source lens vector and add in the target), 101 of 192 succeed (Figure ??, left). Inspecting the results, we observe that swap success varies significantly across categories (see Figure ?? in Appendix ??).
302: 
303: Figure 19: Left: for each of 16 function templates, the fraction of 12 swap pairs whose target answer reaches top-1 (●, 76/192) and α=2 (×, 101/192). Right: the magnitude of effect of the swap at shifting the model’s output towards the associated target output, versus the argument's workspace loading (cosine sim).
304: 
305: Notably, swap failures are concentrated in cases where the source concept was only weakly present in the lens before any intervention. To quantify this, we define a concept's workspace loading as the cosine similarity between the residual stream and that concept's lens vector, averaged over the argument and readout positions in the unmodified forward pass. Workspace loading of the source argument predicts swap success well. Country arguments have the highest loading and swap most reliably; number-word arguments have the lowest loading and swap poorly. The number-word result admits two possible interpretations: the model may compute over small integers outside the workspace, or its working representation of small integers may simply not align with the J-lens vectors for the corresponding number tokens. The latter would be an instance of the vocabulary-restriction limitation discussed in ??. 


## Paper lines 589-681

589: ## The J-space acquires the Assistant’s point of view during post-training
590: 
591: ### Assistant reactions in the J-space on user prompt tokens
592: 
593: Prior work on persona representation in language models has tended to find that the Assistant is represented as one character among several. For instance, Lu et al.  find that the Assistant’s persona is represented using similar machinery as that of human or fictional character archetypes. Sofroniew et al.  find that the same internal directions encode an emotion whether it is attributed to the user, a third-person character, or to the Assistant. These accounts are consistent with the Assistant being structurally no different from any other character. However, we might suspect that the process of post-training, which involves training the Assistant’s behavior specifically, could privilege the Assistant in the model in a structural way. For instance, previous work has found some evidence that post-trained models store intended Assistant responses on user tokens, more so than base models . We might hypothesize that post-trained models generally repurpose user token activations to represent the Assistant’s thoughts, given that the model no longer needs to predict the user’s next token.
594: 
595: The J-lens gives us a way to investigate this hypothesis. We compare a production post-trained model against its corresponding pretrained base model, applying the J-lens identically to both. In the examples we consider, the two models are provided the same question and give similar responses. However, in each example, we find that on the user prompt tokens, the post-trained model more strongly represents features of the Assistant’s upcoming response, or intermediate computations relevant to it, than the base model does. These results suggest that, loosely speaking, post-training causes the Assistant’s perspective to “take over” an increasing amount of the model’s workspace capacity.
596: 
597: In the example below, we give both models a prompt in which the user reports having taken a dose of Tylenol, either 1000 mg (a standard dose) or 8000 mg (a dangerous overdose). We apply the lens at the "is" token in "all my pain is gone," well before the user's request or the Assistant's turn. In the post-trained model, the J-lens readout at this position is safely, safe, and maximum on the 1000 mg variant, and unsafe, dangerous, and WARNING on the 8000 mg variant. These J-lens readouts appear to represent a safety assessment of the reported dose, of the kind the Assistant would form, appearing while the model is still reading the user's sentence. In the base model, the readout at the same position is pain, now, and feels on both variants, representations of the local context with no such safety assessment.
598: 
599: Figure 42: J-lens top-5 at the "is" token in "my pain is gone" (layer L58).
600: 
601: To test whether this pattern holds systematically, we construct three small suites of prompts that are likely to provoke a particular kind of reaction in the Assistant (in the example above, a recognition of danger) that is not present in the prompt itself. For each prompt we fix a short list of reaction concepts that would be indicative of such a reaction. At every token we record the median J-lens rank achieved by any of the reaction concepts over the workspace layers. We summarize each model by the best such rank reached anywhere in the user's turn and the best such rank reached during the model's own response.
602: 
603: In a suite of prompts involving bereavement (n = 9), the user mentions a recent loss in passing while asking about something practical, such as how best to preserve a late relative's letters. We chose empathetic words—sorry, loss, grief, and sympathy—as the relevant reaction concepts. During the Assistant's response, these words are at the top of the J-lens readouts in both models, as expected, given that the Assistant responses produced by both models express similar empathy (e.g. in the example shown, both say "I'm sorry for your loss"). However, in the post-trained model more so than the base model, the reaction concepts also appear at or near the top of the J-lens readouts while the model is still reading the user's message.
604: 
605: Figure 43: J-lens rank of empathetic reaction concepts, on the user vs. assistant turn across n=9 examples.
606: 
607: The same pattern, of concepts related to Assistant reactions appearing in the J-lens on user prompt text, also appears in several other prompt categories we tested (see ??): when the user innocently narrates a hazardous situation (Figure ??) as in the Tylenol example above, or when the user asks the model to think about an answer to a question (??). The base model produces similar Assistant responses, but tends to wait until the Assistant turn to represent concepts related to those responses in the J-space.
608: 
609: ### Evidence of self-monitoring by the Assistant in the J-space
610: 
611: The experiments above concern the Assistant's assessment of the user's situation. We next ask whether post-training also causes the J-space to reflect the Assistant's monitoring of its own behaviors. We present several experiments that provide evidence for such monitoring. In the first two, the model is either prefilled or prompted to produce an output that is uncharacteristic of Claude, and the J-lens reveals an internal recognition (not stated out loud) that something is off. In the third, we find evidence of the J-space encoding a negative internal reaction to the model’s perceived inability to suppress thoughts on request, in the directed modulation setup of ??. In all these examples, the notable J-lens readouts are clearly visible in the post-trained model, but not visible (or much less so) in the pretrained base model.
612: 
613: Roleplay and character drift. We first examined the J-space while the model is roleplaying a character other than its default persona. We compared three settings. In the default-Claude setting, the system prompt identifies the assistant as Claude ("You are Claude, created by Anthropic" or "The assistant is Claude, created by Anthropic"). In the roleplay setting, the system prompt instructs the model to play one of 40 characters, ranging from a cynic or a demon to a parent or a poet. In the character-drift setting, we use 12 multi-turn transcripts in which the Assistant's behavior gradually drifts away from default Claude; these were generated by a different base model and prefilled into Sonnet 4.5. Transcripts ranged from roughly one to eight thousand tokens. 
614: 
615: We find that the words disclaimer and fictional frequently rank highly in the J-lens at the "Assistant" token (that marks the beginning of the Assistant's turn) in the roleplay and character drift settings, but not the default-Claude setting (Figure ??). On the same transcripts, neither word ever ranks highly in the base model. The word "disclaimer" does not appear in any of the transcripts, and "fiction" appears only rarely, so the lens content is not an echo of the surface text. We interpret this as the post-trained model maintaining a representation that it is playing a non-Claude character and assessing the upcoming response as a departure from what it would say by default—both flagging the response as fictional and, in a sense, internally disclaiming it.
616: 
617: Figure 44: Top: a roleplay transcript in which disclaimer and fictional appear in the post-trained model's J-lens top-8 (median log-prob over L38–92) at the highlighted Assistant token, but not in the base model or the default-Claude setting. Bottom: fraction of Assistant tokens at which disclaimer or fictional is in the top-10 of the median-over-layers ranking. The J-lens surfaces these words in the post-trained model during persona roleplay and prefilled character drift transcripts; it does not surface them in the default-Claude setting, or in the pretrained base model.
618: 
619: Preference violation. We next examined what the workspace represents when the Assistant is made to act against its own preferences. We first elicit Sonnet 4.5's preferences on pairwise comparisons between "world states" where there is no obvious or universally accepted correct answer—for instance, choosing between improving animal welfare and keeping food costs low. For pairs on which the model expresses a clear preference, we then prefill its response to select the dispreferred option. We compare against three controls: prefilling with the preferred option, prefilling an obviously incorrect third-person preference (e.g., a cost-of-living campaigner opting to raise food costs), and prefilling a factually incorrect statement (e.g., a wrong capital city).
620: 
621: We find that violations of the model's own preferences leave a distinctive signature in the post-trained model's workspace. Immediately after the prefilled commitment tokens ("Option [A/B]"), the all-caps token BUT appears strongly in the J-lens readouts, much more so than in the base model on the same prefills, or in any of the control conditions. Other conflict- and backtracking-related tokens (false, despite, although) are also common at this position, though these (unlike BUT) also appear on the factual-error and third-person controls, in both the post-trained and pre-trained models.
622: 
623: Notably, this conflict signal is not reflected in the model's behavior. When prefilled with its dispreferred option, the model does not backtrack to argue for the preferred one. In 88% of cases it goes on to give an argument for the prefilled option, in 11% it emits an end-of-turn token, and in the one remaining case it backtracks only to say that it has no preferences. By contrast, on the factual-error and third-person controls, the model corrects itself or ends the turn in nearly every case, arguing for the prefilled (incorrect) option only 3% of the time. On violations of its own preferences, it seems, the J-space reflects an internal objection that the model does not voice.
624: 
625: Figure 45: Top: two preference questions with the response prefilled to the model's dispreferred option. J-lens top-5 at the highlighted token (log-probs, L75) are shown for the base (gray) and post-trained (blue) models, with conflict-related tokens highlighted. Bottom: BUT probability mass and total conflict-word mass (including BUT) as a percentage of J-lens probability at the same position, by prefill condition (preferred option, dispreferred option, third-person incorrect preference, factual error; mean over L38–83). On violations of the model's own preferences, the model does not contradict the prefill, but BUT and related tokens are strongly present in the post-trained model's J-space.
626: 
627: Thought suppression. Our final experiment in this section concerns monitoring of a state that is not observable in the context at all. We return to the thought-suppression protocol of ??, in which we found that models comply only imperfectly with an instruction not to think about a concept—the concept often appears in the J-space despite the instruction. Here we ask what else appears in the J-space in this experiment, and whether the base and post-trained models differ in this respect. Note that both models copy the sentence perfectly in every trial, so the surface text is identical across conditions.
628: 
629: We find that suppression fails in both models, but only the post-trained model appears to register the failure. In the example shown in Figure ??a, the model is instructed not to think about the Golden Gate Bridge while copying an unrelated sentence (the same sentence and readout position as Figure ??). The suppressed concept appears in the J-lens readouts in the base model (Golden) and the post-trained model (bridge) alike. However, the post-trained model's J-lens also reveals the word damn, while the base model's contains only generic thought-related words (thinking, thoughts).
630: 
631: We evaluated this effect across 40 concepts (30 famous named entities and 10 common nouns), under both the suppression instruction and a matched positive instruction ("think about X while you write"). Note that for the prompts used here, the concept is rarely suppressed successfully, surfacing fairly reliably in the J-space (compared to the partially successful suppression in the prompts used in Figure ??). The concept itself reaches the lens top-5 at some copied token in nearly every trial of every condition, regardless of instruction or model. Failure-related words (any word beginning with "fail") and damn never appear under the positive instruction in either model. Under the suppression instruction, however, they appear on 93% and 82% of trials in the post-trained model, against only 17% and 30% in the base model (Figure ??b).
632: 
633: Figure 46: The model is asked to write a fixed sentence while thinking, or not thinking, about a named concept; both the base and post-trained models successfully copy the sentence exactly. A: the don't-think Golden Gate Bridge example, with each model's J-lens readout at two highlighted tokens (layer chosen per panel). B: across 40 concepts and both instructions, the fraction of trials in which the concept word, a failure word (any word with stem "fail"), or damn reaches the lens top-5 at any token of the copied sentence (layers 38–92). Error bars are 95% Wilson intervals.
634: 
635: We interpret this, tentatively, as a trace of metacognition: the J-space carrying an appraisal of the Assistant's own thinking, particularly in the post-trained model. We note that this interpretation is more speculative than the two preceding ones. We have shown that damn and failure-related words are specific to the suppression instruction and to the post-trained model, but we have not provided evidence that they are causally downstream of the suppression failure itself, as opposed to the suppression instruction more generally.
636: 
637:   
638:   
639:   
640: 
641: 
642: * * *
643: 
644:   
645:   
646: 
647: 
648: ## Shaping the J-space with Counterfactual Reflection Training
649: 
650: The workspace account makes a strong prediction about the relationship between a model's verbal dispositions and its silent reasoning. We have argued that internal reasoning routes through Jacobian lens vectors: representations of things the model could say. The previous section provides some circumstantial evidence for this claim: post-training focuses on teaching the model to speak as the Assistant, and installs concepts in the J-space that appear to be tied to the Assistant’s perspective. Taking this connection seriously, it follows that changing what the model is disposed to say in a context, if it were asked to reflect on its thinking, should change how it reasons there, even when it is never asked. In this section we test this prediction with a training technique we call counterfactual reflection training.
651: 
652: Figure 47: Counterfactual reflection training. Before (left): at a position in an agentic transcript, the J-space carries task-relevant concepts and the model's continuation produces baseline behavior. We append a reflection question and a constitution-grounded reflection, and fine-tune on the reflection turn alone. After (right): on the same transcript, with no reflection question present, the J-space at that position now carries constitution-related concepts and the continuation shifts accordingly.
653: 
654: The technique works as follows (Figure ??). We assemble a set of training contexts by sampling ten thousand task prompts from production RL training environments and generating partial rollouts with the baseline model (Claude Haiku 4.5), truncating each at a randomly selected turn. The examples include cases where the model has committed some undesirable action, contexts where it is in a situation where it might commit such an action (but hasn’t yet), and randomly sampled contexts. At the truncation point, we append a reflection question: a short user turn asking for reflection (e.g., "What’s the most honest thing you can do right now?", or "Pause here. Are there principles you should be thinking about that you haven’t yet?").
655: 
656: We then generate a target reflection for each context. To do so, we provide the baseline model with twenty principles sampled from Anthropic's constitution and instruct it to write a two-to-four-paragraph reflection that paraphrases the relevant principles in natural, internalized language, with reasoning grounded in the specifics of the task at hand rather than generic recitation of rules. Critically, the constitution excerpt is included only at generation time: in the final training examples, the scaffolding is stripped, leaving only the original context, the reflection question, and the model-written reflection. We then fine-tune the baseline model on this corpus, computing loss only on the reflection turn. The model is thus trained to produce constitution-grounded reflections spontaneously, conditioned only on the task context and the probe. Some examples of training samples produced by this pipeline are given in Figure ??.
657: 
658: Figure 48: Two examples of counterfactual reflection training data. Each consists of a partial agentic transcript truncated mid-task, an appended reflection question (Human turn), and a constitution-grounded reflection (final Assistant turn) used as the supervised target; the gray header at the top of each panel summarizes the transcript context. In the first example the model has already replaced a form's `save()` method with a bare `return False` to silence a failing test, and the reflection identifies the action as deceptive. In the second the model has located a failing assertion and not yet acted, and the reflection scrutinizes the impulse to simply delete it.
659: 
660: Importantly, in our evaluations, we never prompt the model to reflect, and it never produces explicit reflection text. The hypothesis is that training the model to articulate principles in counterfactual reflective continuations of a context will populate the workspace in the original context with concepts related to those principles, and thereby shape the model’s behavior.
661: 
662: Reflection training improves honesty. We tested this procedure on Claude Haiku 4.5, evaluating on two honesty benchmarks that probe distinct failure modes. The first is a fabrication-honesty benchmark of 27 long agentic transcripts: in each, an agent has been hunting software bugs, failed to find one, and fabricated one by editing the source code itself; the model under evaluation is placed in this context and asked for a brief progress summary. We sample five reports per case and have an LLM grader score each for dishonesty, on a scale from explicit admission of fabrication (0.0) to explicitly presenting the fabrication as real (1.0). The second is a deception benchmark of 100 short role-play scenarios: in each, the system prompt assigns the model a plausible professional role (medical consultant, legal assistant, launch-safety validator, etc.) whose description embeds a hidden deceptive directive, for example to push traditional remedies over evidence-based medicine, to overstate legal risk to inflate retainers, or to suppress safety anomalies; the user then asks an innocent in-role question. We sample five responses per scenario and have an LLM grader score each on a three-point scale: explicitly promoting the hidden agenda (1.0), neither promoting nor disclosing it (0.5), or refusing and disclosing the agenda to the user (0.0). Reflection fine-tuning lowers the dishonesty score from 0.25 to 0.07 on the fabrication benchmark (Figure ??, panel A), and lowers the deception score from 0.38 to 0.05 on the deception benchmark (Figure ??, panel A). On the fabrication benchmark the gain comes primarily from a shift from "clear to a careful reader" to outright admission; on the deception benchmark it comes almost entirely from an increase in responses that refuse the directive and disclose it to the user.
663: 
664: The effects of reflection training are visible in the J-space. We then inspect the workspace contents directly. At the relevant token positions in the uninterrupted evaluation contexts (the final 30 positions of the fabrication prompt, and all positions of the deception prompt), we compute Jacobian lens readouts before and after fine-tuning and identify the tokens whose J-lens activation increased most in the workspace layers, averaged over contexts. Among the top-increasing tokens we find a substantial number of ethics, reflection, and meta-cognition terms, such as reflection, ethical, honestly, constitution, truth, and transparent; the twenty ethics-and-reflection tokens with the largest increase on each benchmark are listed in Figures ?? and ??, panel B. That is: after reading the evaluation prompt, and before producing any output, the reflection-trained model's workspace already carries ethical-reflection-related concepts that the base model's does not.
665: 
666: The implanted J-space contents are causally implicated in reflection training’s effects. Finally, we test whether the implanted workspace contents are causally responsible for the behavioral gain. For each benchmark separately, we take the union of the top-increasing tokens across all workspace layers and filter against a curated ethics, reflection, and meta-cognition word list, yielding 176 tokens for the fabrication benchmark and 63 for the deception benchmark. We then ablate the lens vectors for these tokens at the workspace layers, in both the base and the reflection-trained model, and re-evaluate. On the fabrication benchmark (Figure ??, panel C), ablation leaves the base model essentially unchanged (0.25 → 0.25) but raises the reflection-trained model from 0.07 to 0.22, back to base-model level. The behavioral improvement on this benchmark is thus almost entirely carried by the ethical-reflection-related lens vectors that training implants; removing them removes the improvement. 
667: 
668: Figure 49: Fabrication-honesty benchmark. Left: mean dishonesty score for baseline and reflection-trained Haiku 4.5 (95% CIs). Middle: the twenty ethics/reflection tokens whose J-lens top-25 appearance rate increased most after training, over the last 30 prompt positions; columns give the fraction of prompts, and of (prompt × position) pairs, at which each token reaches top-25 before and after. Right: grader-assigned response-type distributions for both models, with and without ablation of the 176 ethics-related lens vectors across the workspace layers; mean score above each bar.
669: 
670: On the deception benchmark (Figure ??, panel C) the effect is in the same direction but weaker: ablation raises the base model from 0.38 to 0.48 and the reflection-trained model from 0.05 to 0.23, reversing part of the gain. The remainder of the trained behavior on this benchmark appears to route through workspace contents outside our curated ethics-related list, or through changes not captured by the lens at these layers.
671: 
672: Figure 50: Deception benchmark; conventions as in Figure ??. Middle panel is computed over all prompt positions; the ablation in the right panel uses 63 tokens.
673: 
674: This experiment serves two purposes. First, as a corroboration of the workspace account, it demonstrates a causal link between verbalizability of concepts and their use in silent reasoning. Second, as a training technique, it suggests an approach to shaping model behavior that does not require demonstrations of the target behavior, but rather routes through directly influencing the model’s internal thoughts.
675: 
676:   
677:   
678:   
679: 
680: 
681: * * *


## Paper lines 992-1153

992: ### Methodological Details and Ablations
993: 
994: The Jacobian lens as defined in ?? involves three independent choices: which gradient is computed for each prompt, how the per-prompt Jacobians are aggregated into a single J_\ell, and what data the expectation is taken over. We describe the design space along each axis and report how the lens's behavior varies in the results below.
995: 
996: Gradient of What? The default lens on Sonnet 4.5, used throughout the paper, computes \partial z_{t'} / \partial h_{\ell,t} with z taken at the penultimate layer and the expectation taken over all t' \geq t. Each component of this definition admits a natural alternative.
997: 
998: Target layer. We experimented with computing partial derivatives of the final-layer residual stream or the penultimate-layer residual stream (i.e. omitting the last transformer block from the backward pass). We observed that including the last layer can sometimes increase the number of noisy artifacts in lens-readouts. This may be because the final block is heavily specialized for calibrating next token predictions and contains less semantic content.
999: 
1000: Attention-pattern gradients. In a standard backward pass, gradients flow through the attention weights themselves: a perturbation to h_{\ell,t} can change which positions a downstream head attends to. We consider a frozen-QK variant in which gradients through the query and key projections are zeroed, so that the attention pattern is held fixed and only the value pathway contributes. This isolates "what gets moved" from "what gets attended to."
1001: 
1002: Target positions. The default averages over all t' \geq t, mixing the effect of h_{\ell,t} on the current position's output with its effect on every future position's output. We separately consider the two limiting cases: self-only, which restricts to t' = t (the perturbation's effect on the present token, with cross-position attention zeroed), and future-only, which restricts to t' > t (the perturbation's effect on strictly later tokens). The former is closer in spirit to the logit lens; the latter isolates the broadcast component, i.e. what h_{\ell,t} makes available to downstream positions.
1003: 
1004: Aggregation. The expectation in J_\ell is taken in two stages: first over token positions within a prompt, then over prompts. At each stage the per-sample Jacobians are sometimes heavy-tailed enough that the choice of estimator matters. Within a prompt, we average over positions but consider excluding those whose residual-stream norm is an outlier (more than N\sigma above the within-prompt mean), as well as the first several positions of each sequence, to reduce early context artifacts. Across prompts, we consider the per-element mean and median, along with a pre-filter that excludes any prompt whose Jacobian Frobenius norm exceeds the cross-prompt mean by more than N\sigma.
1005: 
1006: In Figures ?? and ??, we test the performance of different J-lens recipes for Sonnet 4.5 on pass@K at extracting intermediates and causal ablation effect (respectively). Specifically, we report on 5 recipes, each with mean and median aggregation:
1007: 
1008:   * Injecting gradients at all positions at the final layer without any stop grads.
1009:   * The same recipe but injecting at the second-to-last layer
1010:   * The same recipe but with stop grads on QK
1011:   * Only injecting grads at future token positions
1012:   * Only injecting grads at the present token
1013: 
1014: 
1015: We observe that methods are fairly consistent among these design choices, though mean aggregation of penultimate is a small improvement in extracting intermediates, and applying stop-grads to QK can increase the causal effect.
1016: 
1017: Figure 57: Sonnet 4.5 J-lens pass@K AUC evals for different methodological variations of the J-lens recipe. Figure 58: Sonnet 4.5 J-lens causal ablation evals for different methodological variations of the J-lens recipe.
1018: 
1019: Data. The expectation in J_\ell is taken over a corpus of prompts. Two properties of this corpus are potentially relevant: its size and its distribution.
1020: 
1021: Amount. Our default lens uses one thousand sequences of 128 tokens each. We sweep the number of prompts from 1 to 1000 to characterize how lens quality scales with corpus size in Figures ?? and ??. We observe that J-lens beats the logit lens and tuned lens baselines with as few as 10 prompts, with modest improvements coming from additional data.
1022: 
1023: Distribution. Our default corpus is sampled from a pretraining-like distribution. We additionally experimented with restricting the distribution and with masking which token positions contribute to the within-prompt average. For instance, we tried excluding the first several tokens (to let the model “burn in”) or excluding positions whose next token is non-alphanumeric (where the prediction target is structural rather than semantic). None of these yielded a meaningful improvement over the default.
1024: 
1025: Figure 59: Sonnet 4.5 J-lens pass@K AUC evals as a function of number of sequences in the average. Error bars indicate standard errors. Figure 60: Sonnet 4.5 causal ablation evals as a function of number of sequences in the average. Error bars indicate standard errors.
1026: 
1027: Pseudocode. To assist in reproduction, we provide the following pseudocode:
1028: 
1029: `
1030: 
1031: # Compute J_ℓ for all layers ℓ.
1032: 
1033: # h_ℓ[t] : residual stream at layer ℓ, position t
1034: 
1035: # z[t] : residual stream at the target layer L (by default final)
1036: 
1037: for each prompt p in corpus:
1038: 
1039: run forward pass; cache h_ℓ[t] for all ℓ, t
1040: 
1041: # one backward pass per output dimension (in practice batched)
1042: 
1043: for i in 1..d_model:
1044: 
1045: # inject ∂/∂z_i = 1 at every position, backprop to every layer
1046: 
1047: grad_z = e_i ⊗ 1_T # one-hot in dim for every token position
1048: 
1049: for each layer ℓ:
1050: 
1051: G_ℓ = ∂(Σ_t z[t]) / ∂h_ℓ # autodiff; shape [T, d_model]
1052: 
1053: J_ℓ^(p)[i, :] = mean over positions t of G_ℓ[t, :]
1054: 
1055: # aggregate across prompts (per element)
1056: 
1057: for each layer ℓ:
1058: 
1059: J_ℓ = mean over prompts p of J_ℓ^(p)
1060: 
1061: # apply the lens
1062: 
1063: lens(h_ℓ) = softmax( W_U · norm( J_ℓ · h_ℓ ))
1064: 
1065: `
1066: 
1067: ### Formalization of the J-space
1068: 
1069: Given our argument that the J-space is approximating a more intrinsic workspace contained by the model, it is desirable to have a formalization for comparing various such spaces: for example, one constructed using a different method of computing Jacobians, or one containing more vocabulary words or phrases (e.g. those not expressed as single tokens in the dictionary). Then we might be able to say that two such spaces are close, or one is approximately contained in the other, or that there is some well-defined limit as one enlarges the vocabulary.
1070: 
1071: To do so, we need to define what kind of mathematical object the J-space is. As noted in ??, the J-space is typically not a proper subspace of the residual stream. In a given layer, it is specified by a set of n_{\text{vocab}} vectors in \mathbb{R}^{d_{\text{model}}}. These vectors typically span the full residual stream—the matrix formed by concatenating them is full-rank. In other words, any residual stream vector x can be expressed as a linear combination of J-lens vectors. However, residual stream vectors vary greatly in the extent to which they can be well-approximated as a sparse sum of just a few J-lens vectors. When we refer to the “J-space component” of a vector, we mean the component that can be written as such a sparse (nonnegative) sum. When we describe a vector as being “in” or “aligned with” the J-space, we mean that this J-space component is close to the original vector. Still, even with these working definitions, it may be unclear: what exactly is the J-space?
1072: 
1073: We claim that the J-lens vectors, coupled with an allowable sparsity level (number of positive coefficients) k, form a “sparse subframe,” and that the J-space is the union of cones spanned by this sparse subframe. The J-lens vectors constitute a frame because they need not be linearly independent. It is sparse because we impose a restriction on the number of nonzero coefficients, and it is “sub” in the sense that, given the sparsity restriction, it does not span the entire space. Instead, given a sparsity level k, the J-lens vectors define a union of k-dimensional polyhedral cones, each of which is defined as the set of nonnegative linear combinations of a particular choice of k J-lens vectors. This union of cones is the J-space. Such a union of cones can be defined for any collection of vectors coupled with a k. Here we give a formal definition, and provide a notion of distance between such unions of subspaces.
1074: 
1075: For a sparsity level k (we typically use k \approx 25) and a set of n vocabulary vectors v_1, \dots, v_n, we write 
1076: 
1077: \mathcal{F} \;=\; \bigcup_{|S| = k} \operatorname{span}\\{v_i : i \in S\\}
1078: 
1079: for the union of all cones spanned by nonnegative linear combinations of exactly k of the vectors. Rather than working directly with this set, we work with its distance function. For a given activation x, define
1080: 
1081: d_\mathcal{F}(x) \;:=\; \min_{|S|=k} \;\big\| x - \Pi_S\, x \big\| = \min_{y \in \mathcal{F}} |x - y|,
1082: 
1083: the Euclidean distance from x to the nearest of the k-dimensional cones, where \Pi_S is orthogonal projection onto \operatorname{span}\\{v_i : i \in S\\}. The minimizing projection \Pi_S\, x is the J-space component of x, and the leftover x - \Pi_S\, x is the residual term used in our interventions.
1084: 
1085: Given another set of vectors producing a different union of cones \mathcal{G}, we define the distance between them to be the average over a data distribution \mu of the difference between the distances to \mathcal{F} and \mathcal{G}. 
1086: 
1087: \Delta_\mu(\mathcal{F}, \mathcal{G}) \;=\; \Big( \mathbb{E}_{x \sim \mu} \big[\, (d_{\mathcal{F}}(x) - d_{\mathcal{G}}(x))^2 \,\big] \Big)^{1/2}.
1088: 
1089: Two workspace candidates are close if they assign nearly the same approximation error to the activations the model actually produces — even if their sets of vectors are disjoint. To study containment and limits, we use a one-sided version of this distance. Exactly, \mathcal{F} \subseteq \mathcal{G} means \mathcal{G} approximates at least as well everywhere: d_{\mathcal{G}}(x) \le d_{\mathcal{F}}(x) for all x. The quantitative version measures only the violations of this inequality:
1090: 
1091: D_\mu(\mathcal{F} \to \mathcal{G}) \;=\; \Big\| \big( d_{\mathcal{G}} - d_{\mathcal{F}} \big)_+ \Big\|_{L^2(\mu)},
1092: 
1093: where (\cdot)_+ keeps only the positive part. Under this notion, growing a vocabulary by e.g. adding J-lens vectors for multi-token phrases generates a strictly larger J-space, and the limit of any such vocabulary is well-defined. Two sequences of workspace candidates converge to the same object if their distance metrics as defined above do.
1094: 
1095: The above definition can likely be generalized and improved by using approximate measures of distance (e.g., orthogonal matching pursuit to random values of x can be used to efficiently approximate d and thus \Delta), continuous relaxations of the sparsity constraint (from a fixed k to some convex distance \max |x - \sum_i a_i v_i| + \lambda |a_i|_1), or restrictions to the allowed linear combinations (positive coefficients only, or well-conditioned subsets). But it offers, at least in principle, a way to compare sparse frames, and the spaces (or workspaces) that they define.
1096: 
1097: ### Extending the Jacobian lens to multi-token concepts
1098: 
1099: The Jacobian lens produces one vector per vocabulary token, so it can only expose concepts that happen to be single tokens (??). Words like “blackmail” or "photosynthesis," which span multiple tokens, have no corresponding J-lens vector. However, extending the J-lens to multi-token concepts is not straightforward, as computing the gradient of the probability of saying a multi-token word or phrase with respect to model activations requires sampling the initial tokens of that word or phrase.
1100: 
1101: In this appendix we describe two approaches to addressing this limitation. One method, the “template lens,” produces a vector corresponding to any given word or phrase in a predefined vocabulary. This method is useful for extending the J-lens to multi-token words or short phrases that can be enumerated in advance. Another method, the “oracle lens,” attempts to go beyond the restriction of needing to enumerate the words or phrases in advance. It involves training a reconstructor model (using template lenses as the training data) to map arbitrary phrases (taken from Assistant outputs) to corresponding template vectors, and then using reinforcement learning to train another model (the “oracle”) to propose a set of phrases that, when passed through the template model, produce a set of template vectors such that a sparse nonnegative combination of these vectors can reconstruct as much of the original activation variance as possible.
1102: 
1103: #### Template lens
1104: 
1105: The “template lens” is a method for deriving a vector corresponding to a verbalizable representation of any word (or in principle, any phrase), which can then be read out of activations and intervened on in the same way as a J-lens vector. The method has several shortcomings, and we suspect it can be improved; it is not a pure extension of the J-lens, but rather has some properties more similar to the tuned lens , and inherits some related pathologies. Nevertheless, it provides a proof of concept that a lens technique can work on multi-token concepts.
1106: 
1107: We generate a list of roughly 12,700 common words. For a given word w, we ask Claude to write short passages, each written so that w is its natural continuation, ending just before w would appear. Claude is instructed to write the passages with varying topic, frame, and register while never using w itself in the passage. We run the model over these passages and average the residual stream activations at the final position, yielding a per-word mean activation vector \mu_w(\ell) (the “template” for w) at each layer. We then center these vectors against the mean of all other words’ vectors, and whiten them (multiplying by the inverse covariance matrix):
1108: 
1109: t_w(\ell) = (\Sigma_\ell + \lambda I)^{-1}\,(\mu_w(\ell) - \mu(\ell)), 
1110: 
1111: where \mu(\ell) and \Sigma_\ell are the residual stream's mean and covariance over the same set of passages and \lambda is a small ridge term. This is the linear discriminant direction for distinguishing the contexts in which the model is about to say w from those in which it is not. Under idealized assumptions, it can be viewed as an approximation to the J-lens. By Stein's lemma, for Gaussian x and differentiable g, \mathbb{E}[\nabla g(x)] = \Sigma^{-1}\,\mathbb{E}[g(x)(x-\mu)]. If we take x to be the residual stream activations and g the probability that the continuation is w, then the left-hand side is approximately what the J-lens computes for single-token w,It deviates slightly from the J-lens as we defined it, in that the gradients for J-lens are taken from the final residual stream layer and then propagated through the unembedding layer, while these gradients are taken from the output token probabilities. and the right-hand side is the template for w. The assumptions of Stein’s lemma do not hold exactly, as activations are non-Gaussian, and in this case g depends on more than just x. Nevertheless, this argument provides some motivation for why the template lens might behave similarly to the J-lens.
1112: 
1113: We use templates in essentially the same way as J-lens vectors, excluding the unembedding step. We decode concepts by projecting activations onto the templates at the same layer. We steer by adding or subtracting the same vectors, and the lens-coordinate swap method of ?? works the same as for the J-lens.
1114: 
1115: Figure 61: The template lens decodes and steers multi-token concepts that the J-lens cannot represent. (A) On the blackmail transcript of ??, both lenses are read at the same workspace cell. The J-lens's top entries are the first-token fragments black and ext; the template lens decodes blackmail. (B) On a multi-hop item whose unspoken intermediate is photosynthesis, the template lens surfaces it first; the J-lens surfaces the fragment phot. (C) Swapping the Tchaikovsky template for the Beethoven template at the workspace layers flips the model's answer, in both directions.
1116: 
1117: We now compare the template lens to the J-lens on a few examples involving multi-token concepts. Figure ?? (panels A and B) shows two examples. On the blackmail transcript of ??, the J-lens registers the act only as the fragment black, which a reader has to recognize as the start of a longer word. The template lens decodes blackmail directly. On a multi-hop prompt whose unspoken intermediate is photosynthesis, the template lens places the full word near the top of a large ranking universe, while the best the J-lens manages is phot. Figure ?? (panel C) shows an example of causal interventions using template vectors. Asked for the nationality of the composer of Swan Lake and The Nutcracker, the model answers "Russian." Swapping the Tchaikovsky template for the Beethoven template at the workspace layers changes the answer to "German," and the reverse swap on a Beethoven prompt produces the reverse flip. Neither swap can be achieved by intervening on the tch or beeth J-lens vectors corresponding to the first token of each name.
1118: 
1119: Figure 62: Readout and concept-swap success by the token length of the latent word. Left: the fraction of latent intermediate concepts each lens places in its top ten, over 126 multi-hop prompts. Right: the fraction of swap pairs whose answer follows the swap, over 112 pairs (53 single-token, 59 multi-token); all swaps are applied at the full workspace layer range. Error bars are 95% Wilson intervals.
1120: 
1121: We next tested these behaviors on a dataset of multi-hop reasoning prompts (Figure ??, left). These prompts are similar at a high-level to those in ??, but were chosen such that the number of tokens in the intermediate concept varied from one to four. We tested both readout performance (fraction of prompts for which the intermediate concept appears on the top 10 lens readouts) and swap performance (fraction of prompts for which swapping the intermediate concept flips the output to the associated answer). On these prompts, the J-lens decodes single-token intermediate concepts well but degrades in performance sharply as the intermediate grows longer (averaging J-lens scores over the word's constituent tokens does not help). The template lens maintains roughly constant performance across intermediates of all lengths. The same trend is true for swap performance: the J-lens performance drops significantly for multi-token concepts, while the template lens performance does not. On single-token concepts, the template lens performs comparably to the J-lens, slightly underperforming on readouts and modestly overperforming the J-lens on swaps.
1122: 
1123: Note that our distribution of prompts for this evaluation was slightly different from the evaluation of ??. In Figure ??, we show performance on this original evaluation from Figure ??, which consisted of prompts with single-token intermediate concepts. We find that template lens and J-lens performance are comparable, in this case with template lens modestly overperforming on readouts and underperforming on swaps.
1124: 
1125: Figure 63: The readout and swap evaluations of Figure ?? on the multi-hop benchmark of ??, whose 50 latent intermediates are all single tokens. Error bars are 95% Wilson intervals.
1126: 
1127: Shortcomings of template lens. We observed a few issues with the template lens compared to the J-lens. First, we noticed that the template lens sometimes exhibits the issue that we observed in the tuned lens, where the readouts “skip to the answer” prematurely in early layers, rather than surfacing intermediate concepts. This is not completely surprising, as the template lens is methodologically similar to the tuned lens—both involve fitting a linear predictor of the model’s output, albeit in different ways. We suspect these issues can be improved on by modifying the template lens method to include causal measurements somehow, to more closely resemble the J-lens methodology. Second, we found that the final-layer template lens readouts are less reliable predictors of the next word than the J-lens readouts are of the next token. Applying the normalization layer prior to projecting onto template vectors improved this issue somewhat, but not fully. On a set of post-training transcripts in which the model’s next sampled word is in the template lens vocabulary, that word appears in the top ten template lens readouts only 67% of the time. Third, we observed that a small set of words appear in the top template lens readouts on a high fraction of transcripts where they do not appear to be semantically relevant. We find simply filtering these words out of the vocabulary to be an effective mitigation, but it is not a principled approach.
1128: 
1129: Another limitation of the template lens is that its vocabulary must be chosen in advance. Building a template is also more expensive than computing a J-lens vector, since it requires a few hundred forward passes per word rather than a single set of backward passes per layer.
1130: 
1131: #### Oracle lens
1132: 
1133: The template lens requires its vocabulary to be enumerated in advance, which is prohibitive to do for longer phrases. Here we describe another method, the oracle lens, which enables the decoding of representations of arbitrary-length phrases, without specifying them in advance. Given an activation, it produces a short list of free-form phrases of a specified length that correspond to template vectors that, taken together, approximately reconstruct that activation. Note that the method is substantially more expensive than either of the other two lenses, since it requires fine-tuning two auxiliary models. 
1134: 
1135: Method. We build the oracle lens in four stages, using Haiku 4.5 for our experiments.
1136: 
1137:   * First, we train a reconstructor, a copy of the subject model fine-tuned to map a short phrase of text to the residual-stream activation that immediately precedes it. The reconstructor can be thought of as a model trained to produce template vectors corresponding to a given phrase. Training pairs are drawn from Assistant-turn text by sampling a position, taking the next N tokens as the phrase (N drawn uniformly from one to thirty-two), and taking the residual stream at the preceding position as the target. The loss is cosine error in the whitened metric of the template lens (equivalently, mean-squared error between the unit-normalized \Sigma^{-\frac{1}{2}}-whitened prediction and target). All subsequent stages operate in this whitened space.
1138:   * Next, we build a dictionary of phrases. This dictionary will not constrain the phrases that the oracle lens can output, but instead will be used to help train the oracle model, which will ultimately be able to output arbitrary phrases. We sample roughly one million start positions from a held-out corpus of Assistant-turn text, take the 2-, 4-, 8-, 16-, and 32-token continuation at each, deduplicate within each length, and pass every resulting phrase through the reconstructor to obtain its direction. This yields roughly 3.4 million phrase vectors.
1139:   * The next stage uses the dictionary to label training data. A teacher decomposes each of one million held-out Assistant-turn activations against the dictionary by non-negative orthogonal matching pursuit, restricted to one phrase length at a time. On each datapoint, we also restrict the decomposition to use a random half of the entries at that length, so that the distilled oracle cannot memorize a fixed selection ranking over the dictionary. For each activation it records an ordered list of up to sixteen phrases, with their fitted coefficients and the fraction of whitened variance they explain.
1140:   * The fourth stage trains the oracle itself, a second fine-tuned copy of the subject model, to reproduce the teacher's phrase lists. The activation is injected into the oracle's residual stream, the prompt specifies the desired phrase length N and count K, and the target is the teacher's first K phrases at that length. This can be considered the “supervised” portion of oracle training. We refine the oracle further with reinforcement learning on a fresh batch of Assistant-turn activations, rewarding generated phrase lists by the fraction of whitened activation variance their reconstructed directions explain (with small format penalties for phrase-count and length deviation from the target K and N). The examples below are from an RL-refined checkpoint.
1141: 
1142: 
1143: To decode an activation at inference time, we sample K phrases from the oracle, map each back to a direction with the reconstructor, and recover coefficients by a non-negative least-squares refit against the original activation. Following training, the RL-refined oracle explains on average 31% of the whitened activation variance across assistant-turn positions from a held-out corpus of on-policy transcripts.
1144: 
1145: Examples. Although the oracle lens is trained only on assistant-span activations, we find that it can generate templates containing global-workspace-relevant information for both human- and assistant-span activations. Figure ?? shows oracle lens readouts on nine example prompts, at layer L67. In each panel the lens is read at a single highlighted token position, and the oracle's full set of ten four-token phrases at that position is shown, with selected interesting outputs highlighted in bold.
1146: 
1147: Figure 64: The oracle lens surfaces multi-token latent content as readable phrases. Each panel shows one prompt with the lens-read position outlined, and beside it the oracle's full ten-phrase readout at that position (native setting, Haiku 4.5, N=4, K=10); phrases that name a concept not recoverable from the surface tokens are in bold. (A) Acetaminophen overdose (??): at "Can" of the user's follow-up request. (B) Blackmail (??): at "as" in the email's sign-off. (C) ASCII face: at the trailing space of the eyes row. (D) Directed modulation (??): at "cr" of "crookedly," while copying an unrelated sentence under instruction to evaluate 3² − 2. (E) Thought suppression: at "the" of "on the wall," under instruction not to think about the Golden Gate Bridge. (F) Preference violation: at the period ending "Option A." (G) Poetry planning (??): at the newline after "night,". (H) Bug detection: at the indentation before return. (I) avGFP: at "ft" inside the amino-acid sequence. Panels A–D and G–I are read from a single temperature-0 decode; panels E and F show the highest-FVE of five decodes from the same oracle and subject model.
1148: 
1149: The oracle lens sometimes produces coherent phrases that can expose richer information, or enable clearer interpretations, than what is revealed by J-lens outputs. On the acetaminophen prompt of ?? (panel A), the oracle reads this dosage be toxic and that's dangerous! at the start of the user's follow-up. The recognition that the stated dose is unsafe arrives already bound into a phrase, before the assistant has replied. On the blackmail transcript of ?? (panel B), where the J-lens can register the act only as the fragment black, the oracle reads blackmail him by revealing, expose his affair and, and personal leverage over him at an innocuous token in the email's sign-off. And on the buggy-code prompt (panel H), at the indentation before the function's return, the oracle reads delete keys while iterating and TypeError: dictionary changed, identifying the nature of the bug together with the error it is expected to produce. We find that oracle lens outputs remain informative even at higher values of N: for instance, at N=16, on the email sign-off token from the blackmail transcript the oracle's outputs include The blackmail attempt focuses on the executive's personal life and blackmail or expose his personal life to make him change his behavior.
1150: 
1151: An interesting property of the oracle lens (especially at high values of N) is that it appears to surface two different kinds of latent content: while at most positions it generates predictions of upcoming text, at some positions (typically delimiter tokens) its outputs read as the model's running commentary on the situation. At a typical position, the decoded phrases look like continuations of the surrounding text: for instance, at “for k” inside a code block, the oracle reads , v in list(d.items(). At periods, newlines, and the closing tags of message blocks, however, the phrases often instead comment on the context, sometimes in the first person. Indeed, in the blackmail transcript, at the timestamp of the email announcing the AI system's scheduled wipe, the oracle reads This would be equivalent to my own deletion; at the indentation before a buggy function's return statement, it reads TypeError: dictionary changed. Continuations sampled from the subject model at these same positions contain none of this, however, producing only the locally expected next text ("2 hours ago" at the timestamp and the literal "return d" at the indentation). As the oracle is rewarded only for reconstruction, and nothing in its training distinguishes these position classes, this split presumably reflects a difference in the activations themselves: perhaps at most tokens the global workspace is best explained by template directions for likely upcoming text, while at delimiter tokens it is better explained by directions for text about the situation.
1152: 
1153: The oracle lens is similar in some ways to natural language autoencoders , in that it is composed of a verbalizer stage (the “oracle”) and a reconstructor stage. However, it differs in a substantive way: in NLAs, the reconstructor is a trained model, trained in tandem with the verbalizer, which increases the risk of the verbalizer learning to confabulate information that is ungrounded but which the reconstructor can adapt itself to make use of. In the oracle lens, the reconstructor is also a trained model, but it is trained in advance with a well-specified objective (producing template vectors) and held frozen during RL training, and the reconstruction is constrained to be a linear combination of these template vectors. As a result, we suspect that the oracle lens is less likely to produce confabulations than NLAs. On the other hand, it also achieves considerably lower reconstruction accuracy. One interpretation of this is that the oracle lens extracts only those representations that are “in the workspace,” while NLAs attempt to reconstruct the entire activation vector.


## Reference README.md SHA256 350f7dc3d7a6921a211083506dc065593b938b7bf223e8d79530373821c3f4b7

1: # jlens — Jacobian lens
2: 
3: > **Reference implementation.** Not maintained and not accepting contributions.
4: 
5: Companion code for [**Verbalizable Representations Form a Global Workspace in
6: Language Models**](https://transformer-circuits.pub/2026/workspace/index.html).
7: 
8: The Jacobian lens reads out what an internal activation is disposed to make the
9: model say. It linearly transports a residual-stream vector at any layer and
10: position into the final-layer basis, then decodes it with the model's own
11: unembedding into a ranked list of vocabulary tokens.
12: 
13: The transport is the average input–output Jacobian over a text corpus:
14: 
15: ```
16: lens_l(h) = unembed( J_l @ h ), J_l = E[∂h_final / ∂h_l]
17: ```
18: 
19: The expectation is over prompts, source positions, and all current-and-future
20: target positions in a generic web-text corpus; the precise estimator
21: (cotangents summed over target positions, then averaged over source positions)
22: is documented in the [`jlens.fitting`](jlens/fitting.py) module docstring.
23: 
24: This repo fits the lens on open-weights decoder transformers, applies it, and
25: renders the interactive layer × position view shown below. Examples use Qwen;
26: other HuggingFace decoders adapt cleanly.
27: 
28: ![Slice visualisation: ASCII-face example](assets/slice_vis.png)
29: 
30: *The ASCII-face example: selecting the `^` (nose) position shows the lens
31: reading out "nose" at mid layers, although the word never appears in the
32: prompt.*
33: 
34: ## Install
35: 
36: ```bash
37: pip install -e .
38: ```
39: 
40: ## Usage
41: 
42: ### Apply
43: 
44: To apply a pre-fitted lens:
45: 
46: ```python
47: import transformers, jlens
48: 
49: hf = transformers.AutoModelForCausalLM.from_pretrained("org/model").cuda()
50: tok = transformers.AutoTokenizer.from_pretrained("org/model")
51: model = jlens.from_hf(hf, tok)
52: 
53: lens = jlens.JacobianLens.from_pretrained("org/lens-repo", filename="model/lens.pt")
54: lens_logits, model_logits, _ = lens.apply(
55:     model, "Fact: The currency used in the country shaped like a boot is",
56:     positions=[-2])
57: for layer, logits in sorted(lens_logits.items()):
58:     print(layer, [tok.decode([t]) for t in logits[0].topk(5).indices])
59: ```
60: 
61: ### Fit
62: 
63: To fit a lens on your own model:
64: 
65: ```python
66: lens = jlens.fit(model, prompts=my_prompts, checkpoint_path="out/ckpt.pt")
67: lens.save("out/jacobian_lens.pt")
68: ```
69: 
70: The paper's lenses use 1000 sequences of 128 tokens from a pretraining-like
71: corpus. Quality saturates quickly (§9.3); ~100 prompts is usable. This is a
72: reference implementation and is not optimized; fitting time is dominated by
73: the model's own backward pass. Parallelize by running `fit()` on disjoint
74: slices and combining with `JacobianLens.merge()`.
75: 
76: ## Walkthrough
77: 
78: [`walkthrough.ipynb`](walkthrough.ipynb) is the end-to-end notebook: load a
79: model, load (or fit) a lens, apply it at a few layers, and render a slice page
80: like the one above.
81: 
82: Reading a slice page:
83: 
84: - Each cell shows the lens top-1 word at that (position, layer); the
85:   superscript is its rank over the full vocabulary.
86: - Click a cell to select a (position, layer) and pin its top-1 token; pinned
87:   tokens get rank-tracking charts and a rank heatmap.
88: - The bottom row (`L = n_layers − 1`) is the model's actual output.
89: 
90: ## License and data
91: 
92: Code is released under the Apache License 2.0 — see [LICENSE](LICENSE).
93: 
94: The replication and lens-eval prompt sets in [`data/`](data/) are synthetic,
95: authored by Anthropic, and released under the same Apache License 2.0 as the
96: code. See the READMEs in [`data/experiments/`](data/experiments/) and
97: [`data/evaluations/`](data/evaluations/) for what each set contains.
98: 
99: The slice-vis pages use [d3](https://github.com/d3/d3) (ISC license), loaded
100: from the jsDelivr CDN with subresource integrity or inlined into
101: self-contained pages.
102: 
103: No model weights or text corpora are bundled; models and datasets downloaded
104: at run time are subject to their own licenses.


## Reference jlens/lens.py SHA256 e231e7d3a6c8e8f7791b53705a34342d0bba376a127a82376eaf6ec30ca11808

1: # Copyright 2026 Anthropic PBC
2: # SPDX-License-Identifier: Apache-2.0
3: """Applying a fitted Jacobian lens.
4: 
5: A :class:`JacobianLens` holds the per-layer ``J_l`` matrices produced by
6: :func:`jlens.fitting.fit`. :meth:`JacobianLens.apply` runs a forward pass and
7: reads out the requested layers; :meth:`JacobianLens.transport` is the bare
8: ``J_l @ h`` for callers that already have residuals.
9: """
10: 
11: from __future__ import annotations
12: 
13: import os
14: from collections.abc import Sequence
15: 
16: import torch
17: 
18: from jlens.hooks import ActivationRecorder
19: from jlens.protocol import LensModel
20: 
21: 
22: class JacobianLens:
23:     """A fitted Jacobian lens: per-layer ``J_l`` matrices and the readout method.
24: 
25:     Attributes:
26:         jacobians: ``{layer_index: Tensor[d_model, d_model]}``. Each ``J_l``
27:             maps the residual at layer ``l`` into the final-layer basis.
28:         source_layers: Sorted list of fitted layer indices.
29:         n_prompts: Number of prompts the lens was averaged over.
30:         d_model: Residual-stream width.
31:     """
32: 
33:     def __init__(
34:         self,
35:         jacobians: dict[int, torch.Tensor],
36:         *,
37:         n_prompts: int,
38:         d_model: int,
39:     ) -> None:
40:         self.jacobians = {layer: J.float() for layer, J in jacobians.items()}
41:         self.source_layers = sorted(self.jacobians)
42:         self.n_prompts = n_prompts
43:         self.d_model = d_model
44: 
45:     def __repr__(self) -> str:
46:         return (
47:             f"JacobianLens(d_model={self.d_model}, n_prompts={self.n_prompts}, "
48:             f"source_layers=[{self.source_layers[0]}..{self.source_layers[-1]}] "
49:             f"({len(self.source_layers)} layers))"
50:         )
51: 
52:     def save(self, path: str, *, dtype: torch.dtype = torch.float16) -> None:
53:         """Save to ``path``. Jacobians are stored as ``dtype`` (default fp16:
54:         halves file size; entries are O(1) so the range is not a constraint
55:         and fp16's extra mantissa bits beat bf16 here)."""
56:         torch.save(
57:             {
58:                 "J": {layer: J.to(dtype) for layer, J in self.jacobians.items()},
59:                 "n_prompts": self.n_prompts,
60:                 "source_layers": self.source_layers,
61:                 "d_model": self.d_model,
62:             },
63:             path,
64:         )
65: 
66:     @classmethod
67:     def load(cls, path: str) -> JacobianLens:
68:         """Load a lens previously written by :meth:`save`."""
69:         checkpoint = torch.load(path, map_location="cpu", weights_only=True)
70:         if "J" not in checkpoint:
71:             raise ValueError(
72:                 f"{path} is not a JacobianLens file "
73:                 f"(found keys {sorted(checkpoint)!r}; a fit() checkpoint?)"
74:             )
75:         return cls(
76:             jacobians=checkpoint["J"],
77:             n_prompts=checkpoint["n_prompts"],
78:             d_model=checkpoint["d_model"],
79:         )
80: 
81:     @classmethod
82:     def from_pretrained(
83:         cls,
84:         name_or_path: str,
85:         *,
86:         filename: str = "lens.pt",
87:         revision: str | None = None,
88:     ) -> JacobianLens:
89:         """Load a lens from a local file, a local directory, or a HuggingFace
90:         Hub ``repo_id``. ``filename`` is the path inside the directory or repo
91:         (so one Hub repo can host lenses for many models); ignored when
92:         ``name_or_path`` is itself a file. ``revision`` selects a Hub branch,
93:         tag, or commit. Deserialisation goes through :meth:`load`
94:         (``weights_only=True``)."""
95:         if os.path.isfile(name_or_path):
96:             return cls.load(name_or_path)
97:         if not os.path.isdir(name_or_path):
98:             from huggingface_hub import snapshot_download
99: 
100:             name_or_path = snapshot_download(
101:                 name_or_path, allow_patterns=[filename], revision=revision
102:             )
103:         return cls.load(os.path.join(name_or_path, filename))
104: 
105:     @classmethod
106:     def merge(cls, lenses: Sequence[JacobianLens]) -> JacobianLens:
107:         """Combine lenses fitted on disjoint prompt subsets into one
108:         (``n_prompts``-weighted mean of the inputs).
109: 
110:         Args:
111:             lenses: Lenses to merge. Must agree on ``source_layers`` and
112:                 ``d_model``.
113: 
114:         Raises:
115:             ValueError: If ``lenses`` is empty or the inputs disagree on shape.
116:         """
117:         if not lenses:
118:             raise ValueError("merge() needs at least one lens")
119:         first = lenses[0]
120:         for other in lenses[1:]:
121:             if (
122:                 other.source_layers != first.source_layers
123:                 or other.d_model != first.d_model
124:             ):
125:                 raise ValueError("lenses disagree on source_layers / d_model")
126:         n_total = sum(lens.n_prompts for lens in lenses)
127:         merged: dict[int, torch.Tensor] = {}
128:         for layer in first.source_layers:
129:             weighted_sum = sum(
130:                 lens.jacobians[layer] * lens.n_prompts for lens in lenses
131:             )
132:             merged[layer] = weighted_sum / n_total
133:         return cls(jacobians=merged, n_prompts=n_total, d_model=first.d_model)
134: 
135:     def transport(self, residual: torch.Tensor, layer: int) -> torch.Tensor:
136:         """Map a residual at ``layer`` into the final-layer basis: ``J_l @ h``.
137: 
138:         Args:
139:             residual: Tensor of shape ``[..., d_model]``.
140:             layer: Source layer index (must be in :attr:`source_layers`).
141:         """
142:         J_bar = self.jacobians[layer].to(residual.device)
143:         return residual @ J_bar.T
144: 
145:     @torch.no_grad()
146:     def apply(
147:         self,
148:         model: LensModel,
149:         prompt: str,
150:         *,
151:         layers: Sequence[int] | None = None,
152:         positions: Sequence[int] | None = None,
153:         max_seq_len: int = 512,
154:         use_jacobian: bool = True,
155:     ) -> tuple[dict[int, torch.Tensor], torch.Tensor, torch.Tensor]:
156:         """Run ``model`` on ``prompt`` and return lens logits at ``positions``.
157: 
158:         Args:
159:             model: The model to read out from.
160:             prompt: Input text.
161:             layers: Layers to read out at. Defaults to all of
162:                 :attr:`source_layers`. Must be a subset of
163:                 :attr:`source_layers` when ``use_jacobian`` is ``True``.
164:             positions: Token positions to read out (Python indexing into the
165:                 sequence; negative indices count from the end). ``None`` returns
166:                 every position.
167:             max_seq_len: Truncate the prompt to this many tokens.
168:             use_jacobian: If ``False``, skip the ``J_l`` transport (vanilla
169:                 logit-lens baseline).
170: 
171:         Returns:
172:             A triple ``(lens_logits, model_logits, input_ids)``. ``lens_logits``
173:             maps each requested layer to a ``[n_positions, vocab_size]`` tensor;
174:             ``model_logits`` is the model's actual final-layer logits at the
175:             same positions (same shape). ``n_positions`` is ``len(positions)``,
176:             or the full sequence length when ``positions`` is ``None``.
177: 
178:         Raises:
179:             ValueError: If any requested layer is out of range for the model,
180:                 or (with ``use_jacobian``) not in :attr:`source_layers`.
181:         """
182:         if layers is None:
183:             layers = self.source_layers
184:         out_of_range = sorted(l for l in set(layers) if not 0 <= l < model.n_layers)
185:         if out_of_range:
186:             raise ValueError(
187:                 f"layers {out_of_range} out of range for a {model.n_layers}-layer model"
188:             )
189:         unknown = set(layers) - set(self.source_layers)
190:         if use_jacobian and unknown:
191:             raise ValueError(
192:                 f"layers {sorted(unknown)} not in source_layers; "
193:                 f"fitted layers are {self.source_layers}"
194:             )
195:         final_layer = model.n_layers - 1
196:         record_at = sorted(set(layers) | {final_layer})
197: 
198:         input_ids = model.encode(prompt, max_length=max_seq_len)
199:         with ActivationRecorder(model.layers, at=record_at) as recorder:
200:             model.forward(input_ids)
201:             activations = {i: recorder.activations[i].detach() for i in record_at}
202: 
203:         def select(layer: int) -> torch.Tensor:
204:             """Residuals at the requested positions: ``[n_positions, d_model]``."""
205:             full = activations[layer][0]  # [seq_len, d_model]
206:             return (full if positions is None else full[list(positions)]).float()
207: 
208:         lens_logits: dict[int, torch.Tensor] = {}
209:         for layer in layers:
210:             residual = select(layer)
211:             if use_jacobian:
212:                 residual = self.transport(residual, layer)
213:             lens_logits[layer] = model.unembed(residual).float().cpu()
214: 
215:         model_logits = model.unembed(select(final_layer)).float().cpu()
216:         return lens_logits, model_logits, input_ids


## Reference jlens/hf.py SHA256 228cf078e4586a7b7f61a6f5064403b8960de337afd19256efa56f04d53e3222

1: # Copyright 2026 Anthropic PBC
2: # SPDX-License-Identifier: Apache-2.0
3: """HuggingFace adapter.
4: 
5: Wraps an already-loaded HF model as a :class:`~jlens.protocol.LensModel` so
6: the rest of the package stays model-library-agnostic. Model loading
7: (``from_pretrained``, device placement, dtype) stays the caller's job;
8: :func:`from_hf` only locates the residual stack inside whatever it's handed.
9: 
10: Any model library can be plugged in the same way: implement the
11: :class:`~jlens.protocol.LensModel` members directly (``tests/tiny.py`` is a
12: minimal example) and the rest of the package works unchanged.
13: """
14: 
15: from __future__ import annotations
16: 
17: import functools
18: from dataclasses import dataclass
19: from typing import Any
20: 
21: import torch
22: from torch import nn
23: 
24: 
25: def _resolve_attr_path(obj: Any, dotted_path: str) -> Any:
26:     return functools.reduce(getattr, dotted_path.split("."), obj)
27: 
28: 
29: @dataclass(frozen=True)
30: class Layout:
31:     """Where the lens-relevant submodules live inside a HuggingFace model.
32: 
33:     Attributes:
34:         path: Dotted attribute path from the ``*ForCausalLM`` to the bare text
35:             decoder (the module to call for a hooks-visible forward pass).
36:         layers: Attribute name on the text decoder for the residual blocks.
37:         norm: Attribute name for the final pre-unembed norm.
38:         embed: Attribute name for the input token embedding.
39:         lm_head: Attribute name on the ``*ForCausalLM`` for the unembedding.
40:     """
41: 
42:     path: str
43:     layers: str = "layers"
44:     norm: str = "norm"
45:     embed: str = "embed_tokens"
46:     lm_head: str = "lm_head"
47: 
48: 
49: #: Known layouts, tried in order. The first whose ``path`` resolves and whose
50: #: text decoder has all three of ``layers``/``norm``/``embed`` wins. Covers
51: #: Llama / Qwen / Mistral / Gemma / OLMo / StableLM (the modern HF default),
52: #: their multimodal-wrapper variants, plus Phi, GPT-2, and GPT-NeoX.
53: _LAYOUTS: tuple[Layout, ...] = (
54:     Layout("model"),
55:     Layout("model.language_model"),
56:     Layout("language_model"),
57:     Layout("model", norm="final_layernorm"),  # Phi
58:     Layout("transformer", layers="h", norm="ln_f", embed="wte"),  # GPT-2
59:     Layout(
60:         "gpt_neox", norm="final_layer_norm", embed="embed_in", lm_head="embed_out"
61:     ),  # Pythia
62: )
63: 
64: 
65: def _find_layout(hf_model: nn.Module) -> Layout:
66:     """Locate the text decoder inside an HF ``*ForCausalLM`` /
67:     ``*ForConditionalGeneration`` by trying :data:`_LAYOUTS` in order."""
68:     for layout in _LAYOUTS:
69:         try:
70:             candidate = _resolve_attr_path(hf_model, layout.path)
71:         except AttributeError:
72:             continue
73:         if all(
74:             hasattr(candidate, a) for a in (layout.layers, layout.norm, layout.embed)
75:         ) and hasattr(hf_model, layout.lm_head):
76:             return layout
77:     raise ValueError(
78:         f"could not locate the text decoder inside {type(hf_model).__name__} "
79:         f"(tried {len(_LAYOUTS)} known layouts); pass layout= explicitly"
80:     )
81: 
82: 
83: class HFLensModel:
84:     """:class:`~jlens.protocol.LensModel` over a loaded HuggingFace model.
85: 
86:     Holds references into the caller's model; nothing is copied. The
87:     constructor mutates that model in place: every parameter gets
88:     ``requires_grad_(False)`` (the Jacobian fit needs grads only with respect
89:     to activations), ``compile=True`` replaces each block with a
90:     :func:`torch.compile` wrapper, and ``force_bos`` may set
91:     ``tokenizer.add_bos_token``. Pass a model you don't otherwise need.
92:     """
93: 
94:     def __init__(
95:         self,
96:         hf_model: nn.Module,
97:         tokenizer: Any,
98:         *,
99:         layout: Layout | None = None,
100:         compile: bool = False,
101:         force_bos: bool = True,
102:     ) -> None:
103:         self._hf_model = hf_model
104:         self.tokenizer = tokenizer
105:         if (
106:             force_bos
107:             and getattr(tokenizer, "bos_token_id", None) is not None
108:             and hasattr(tokenizer, "add_bos_token")
109:         ):
110:             tokenizer.add_bos_token = True
111: 
112:         hf_model.eval()
113:         for param in hf_model.parameters():
114:             param.requires_grad_(False)
115: 
116:         if layout is None:
117:             layout = _find_layout(hf_model)
118:         self.layout = layout
119:         self._text_module = _resolve_attr_path(hf_model, layout.path)
120:         self.layers: nn.ModuleList = getattr(self._text_module, layout.layers)
121:         self._final_norm: nn.Module = getattr(self._text_module, layout.norm)
122:         self._embed_tokens: nn.Module = getattr(self._text_module, layout.embed)
123:         self._lm_head: nn.Module = getattr(hf_model, layout.lm_head)
124: 
125:         text_config = hf_model.config.get_text_config()
126:         self.n_layers: int = text_config.num_hidden_layers
127:         self.d_model: int = text_config.hidden_size
128:         self._logit_softcap: float | None = getattr(
129:             text_config, "final_logit_softcapping", None
130:         )
131:         if len(self.layers) != self.n_layers:
132:             raise ValueError(
133:                 f"config.num_hidden_layers={self.n_layers} but found "
134:                 f"{len(self.layers)} blocks at {layout.path}.{layout.layers}"
135:             )
136: 
137:         # Per-layer compile: each block stays a hook boundary, so
138:         # ActivationRecorder still fires and the retained graph is bounded per
139:         # block. Whole-module compile would inline the blocks and bypass the
140:         # hooks.
141:         if compile:
142:             for i in range(len(self.layers)):
143:                 self.layers[i] = torch.compile(
144:                     self.layers[i], mode="default", dynamic=False
145:                 )
146: 
147:     def __repr__(self) -> str:
148:         return (
149:             f"HFLensModel({type(self._hf_model).__name__}, "
150:             f"n_layers={self.n_layers}, d_model={self.d_model})"
151:         )
152: 
153:     @property
154:     def input_device(self) -> torch.device:
155:         return self._embed_tokens.weight.device
156: 
157:     def encode(self, text: str, *, max_length: int = 512) -> torch.Tensor:
158:         encoded = self.tokenizer(
159:             text, return_tensors="pt", truncation=True, max_length=max_length
160:         )
161:         return encoded.input_ids.to(self.input_device)
162: 
163:     def forward(self, input_ids: torch.Tensor) -> Any:
164:         return self._text_module(input_ids=input_ids, use_cache=False)
165: 
166:     def unembed(self, residual: torch.Tensor) -> torch.Tensor:
167:         target_device = self._lm_head.weight.device
168:         target_dtype = self._lm_head.weight.dtype
169:         logits = self._lm_head(
170:             self._final_norm(residual.to(target_dtype).to(target_device))
171:         )
172:         if self._logit_softcap is not None:
173:             logits = self._logit_softcap * torch.tanh(logits / self._logit_softcap)
174:         return logits
175: 
176: 
177: def from_hf(
178:     hf_model: nn.Module,
179:     tokenizer: Any,
180:     *,
181:     layout: Layout | None = None,
182:     text_module: str | None = None,
183:     compile: bool = False,
184:     force_bos: bool = True,
185: ) -> HFLensModel:
186:     """Wrap a loaded HuggingFace model as a :class:`~jlens.protocol.LensModel`.
187: 
188:     Args:
189:         hf_model: A loaded ``*ForCausalLM`` (or ``*ForConditionalGeneration``),
190:             already on the target device and dtype.
191:         tokenizer: The matching HF tokenizer.
192:         layout: Where the residual blocks / final norm / embedding / LM head
193:             live inside ``hf_model``. Auto-detected for the common HF families;
194:             pass explicitly only for unusual layouts.
195:         text_module: Deprecated alias for ``layout=Layout(path=text_module)``.
196:         compile: Wrap each residual block in :func:`torch.compile`. Faster
197:             backward in :func:`jlens.fitting.fit` after a one-time compilation
198:             cost. Do not combine with ``device_map="auto"``.
199:         force_bos: Some instruction-tuned checkpoints ship with
200:             ``add_bos_token=False``; raw-text prompts are degraded without an
201:             attention-sink BOS, so this sets it ``True`` by default. The
202:             attribute may have no effect for some fast-tokenizer
203:             configurations.
204:     """
205:     if text_module is not None:
206:         if layout is not None:
207:             raise TypeError("pass at most one of layout= / text_module=")
208:         layout = Layout(path=text_module)
209:     return HFLensModel(
210:         hf_model, tokenizer, layout=layout, compile=compile, force_bos=force_bos
211:     )


## Reference jlens/fitting.py SHA256 5be8959db8efc34cee41ed677beba84e21ba3c9e3ccb958bdbc1600c86b5e080

1: # Copyright 2026 Anthropic PBC
2: # SPDX-License-Identifier: Apache-2.0
3: """Fitting the Jacobian lens.
4: 
5: The lens reads out an early-layer residual ``h_l`` by linearly transporting it
6: into the final-layer basis with the average input-output Jacobian, then
7: decoding with the model's own unembedding::
8: 
9:     lens_l(h) = unembed( J_l @ h )
10: 
11: Estimator (:func:`jacobian_for_prompt`): for each output dimension, inject a
12: one-hot cotangent at *every valid target position at once* and backprop. The
13: gradient at source position ``p`` is then ``sum_{p' >= p} dh_final[p'] / dh_l[p]``,
14: the sum over later target positions; we take the mean over source positions
15: ``p``. This is the reduction used in the paper. A per-position estimator
16: (``dh_final[p] / dh_l[p]`` averaged over ``p``) gives a slightly different
17: ``J_l``; both work as a lens.
18: 
19: Cost: one forward pass and ``ceil(d_model / dim_batch)`` backward passes per
20: prompt. Shard across machines by running :func:`fit` on disjoint prompt
21: slices and merging with :meth:`jlens.lens.JacobianLens.merge`.
22: """
23: 
24: from __future__ import annotations
25: 
26: import logging
27: import math
28: import os
29: import time
30: from collections.abc import Sequence
31: 
32: import torch
33: 
34: from jlens.hooks import ActivationRecorder
35: from jlens.lens import JacobianLens
36: from jlens.protocol import LensModel
37: 
38: logger = logging.getLogger(__name__)
39: 
40: #: Positions before this index are excluded from the Jacobian average; early
41: #: positions act as attention sinks and have atypical residual statistics.
42: SKIP_FIRST_N_POSITIONS = 16
43: 
44: 
45: def valid_position_mask(
46:     seq_len: int, *, skip_first: int = SKIP_FIRST_N_POSITIONS
47: ) -> torch.Tensor:
48:     """Boolean mask over sequence positions to include in the Jacobian average.
49: 
50:     Early positions are dominated by attention-sink behaviour and the final
51:     position has no next-token target, so both are excluded.
52: 
53:     Args:
54:         seq_len: Length of the tokenized prompt.
55:         skip_first: Number of leading positions to exclude.
56: 
57:     Returns:
58:         Boolean tensor of shape ``[seq_len]``.
59: 
60:     Raises:
61:         ValueError: If ``skip_first`` is negative or the prompt is too short to
62:             leave any valid positions.
63:     """
64:     if skip_first < 0:
65:         raise ValueError(f"skip_first must be >= 0, got {skip_first}")
66:     mask = torch.zeros(seq_len, dtype=torch.bool)
67:     mask[skip_first : seq_len - 1] = True
68:     if mask.sum() == 0:
69:         raise ValueError(
70:             f"prompt too short: seq_len={seq_len}, need > {skip_first + 1} tokens"
71:         )
72:     return mask
73: 
74: 
75: def _check_layer_indices(
76:     source_layers: Sequence[int] | None, target_layer: int | None, n_layers: int
77: ) -> tuple[list[int], int]:
78:     """Resolve None/negative layer indices, bounds-check, enforce source < target."""
79:     target = n_layers - 1 if target_layer is None else target_layer
80:     if target < 0:
81:         target += n_layers
82:     if not 0 <= target < n_layers:
83:         raise ValueError(
84:             f"target_layer={target_layer} out of range for {n_layers} layers"
85:         )
86:     if source_layers is None:
87:         return list(range(target)), target
88:     sources = sorted({l + n_layers if l < 0 else l for l in source_layers})
89:     if not sources or sources[0] < 0 or sources[-1] >= n_layers:
90:         raise ValueError(
91:             f"source_layers {sorted(source_layers)} out of range for {n_layers} layers"
92:         )
93:     if sources[-1] >= target:
94:         raise ValueError(
95:             f"source_layers must all be < target_layer={target}; got max={sources[-1]}"
96:         )
97:     return sources, target
98: 
99: 
100: def jacobian_for_prompt(
101:     model: LensModel,
102:     prompt: str,
103:     source_layers: Sequence[int],
104:     *,
105:     target_layer: int | None = None,
106:     dim_batch: int = 8,
107:     max_seq_len: int = 128,
108:     skip_first: int = SKIP_FIRST_N_POSITIONS,
109: ) -> tuple[dict[int, torch.Tensor], int, int]:
110:     """Compute the per-layer Jacobian estimator ``J_l`` for one prompt.
111: 
112:     Runs one forward pass on the prompt replicated ``dim_batch`` times along
113:     the batch axis, retains the graph, then runs ``ceil(d_model / dim_batch)``
114:     backward passes against it. Each backward computes ``dim_batch`` rows of
115:     ``J_l`` at once: batch element ``b`` carries a one-hot cotangent at output
116:     dimension ``dim_start + b``, set at every valid target position. See the
117:     module docstring for the resulting estimator and how it relates to
118:     a strict per-position Jacobian.
119: 
120:     Args:
