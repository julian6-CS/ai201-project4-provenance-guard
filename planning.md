
************************************************************************************************************************************

Project Summary: Provenance Guard is an backend system that upon receiving a string it classifies whether the content provided is produced by an artifical intelligence. Upon receiving the content, the string is verified across the first signal where an llm measures the semantic consistency, linguistic patterns, and overall writing style to produce a float value representing the confidence score of how AI the llm believes the input is. The second signal is a stylometric evaluation which measures the sentence length variance, punctuation density, and vocabulary diversity present within the input. Both signals are evaluated to assign a label to the input and a confidence scoring attributed to how AI the api believes the input is. This information is then stored within the audit log within a sqlite database where the content_id, attribution, confidence scoring, label, and status is then stored. This label and the confidence scoring is then returned for the user. If the user would like to appeal this decision, it is possible by providing the content id related to to the decision they would like to appeal and the status of this entry will be changed to reflect the need for a moderator to review it.

************************************************************************************************************************************

Detection signals: What are your 2+ signals? What does each one measure? What does each signal's output look like (a score between 0–1? a binary flag?), and how will you combine them into a single confidence score?

Signal 1 (STYLOMETRIC HEURISTICS) : Specifically, this will measure the sentence length variance, vocabulary diversity, and the punctuation diversity within any input. Sentence length variance is a structural feature within writing that varies the most within human writing, in contrast, some AI-generated text has shown to be relatively uniform in this aspect. Evaluating vocabulary diversity and punctuation density is very useful since some AI-generated content follows a consistent punctuation pattern or limited vocabulary, but this metric only contributes a small portion to the signal. The reasoning behind this is that some users have a limited understanding of punctuation or deeply ingrained or learned habits that could be misclassified as AI. In addition to this, if a user writes on a genre or a topic foreign to their understanding, they are more likely to repeat certain words or phrases. The score provided by this signal is from 0-0.10 where sentence length variety makes up 52% of this scoring, meanwhile, vocabulary density and punctuation density each make up to 24% of this score.

Signal 2 (LLM CLASSIFIER): The input will be provided to an LLM where it will evaluate the text as a whole to analyze the semantic coherence, consistency of tone, discourse flow between sentences, predictable phrasing, use of formulaic language, whether the text is unusually balanced, linguistic patterns often seen in AI generated content, the use of generic or broad applicable statements, or use of phrasing associated with work produce by large language models. Since there is no equation or framework that we can provide to the llm where a statistic can be reliably calculated, the llm will make a holistic judgement and give a attribution score from 0 - 1.0 representing how AI-influenced the provided text is. We will also provide some guidance on how to base their numeric scoring.

The two signals will then be used to calculate the AI-attribution score by the following formula, (Signal 2) * 0.90 + Signal 1 (0.10), largely to avoid possible false positive since Signal 1 has some overlap with normal human behavior and keeping its' influence under what's needed to progress to the next more severe label will help avoid any misclassifications.

The calculation of the confidence score differs depending on the range the attribution or llm score falls in, s = llm_score

if 0.0 <= s <= 0.45:
    confidence = 0.5 + 0.5 ( 1 - (s / 0.45))
    reasoning: The closer the score is to 0, the system is more confident that the text provided was written by a human rather than AI-generated.
if 0.45 < s <= 0.60:
    confidence = 1 - 0.5 (|s - 0.525 | / 0.075)
    reasoning: The closer the score is to the middle of the uncertain range, the more confident the system is that it is unsure whether it is AI-generated or human-written.

if 0.60 < s <= 1.00 :
    confidence = 0.5 + 0.5((s - 0.60) / 0.40 )

    reasoning: The closer the attribution score is to the upper limit of 1, the system has more confidence in defining the label as AI-generated due.

************************************************************************************************************************************
Uncertainty representation: What does a confidence score of 0.6 mean to your system? How will you map raw signal outputs to a calibrated score? What threshold separates "likely AI" from "uncertain" from "likely human"?

A confidence score of 0.6 can be interpretted as the system being unsure whether the current label best encapsulates the current input, in other words, how sure it is regarding it's classification. There is one score that is produced prior to the confidence score, which is the attribution score or llm_score which has a range of 0-1.0 where 0-0.45 is classified as human-written, 0.450001-0.6001 is classified as uncertain, and 0.60001-1.00 is classified as AI-generated. The confidence score is then calculated using this llm_score, if it falls within the range of 0-0.45 the closer the score is to the upper bound of 0.45 the less confident the score is, if it falls within the 0.450001-0.60 range the farther it is from 0.525 the less confident it is of its' label, and if it falls between the 0.6001-1.00 range then the score will be higher the further it is from 0.60 or the closer it is to the ceiling of 1.00.


************************************************************************************************************************************
Transparency label design: What exact text will the label show for a high-confidence AI result? A high-confidence human result? An uncertain result? Write out the three label variants now, before you build the UI.

Human-Written: There is a high confidence that this text was written by a human with no visible influence from AI

Uncertain: The system cannot confidently classify whether this text is written by a human or generated by an AI-model

AI-Generated: The system has a high confidence that the text provided was generated by an AI-model

************************************************************************************************************************************
Appeals workflow: Who can submit an appeal? What information do they provide? What does the system do when an appeal is received — what status changes, what gets logged? What would a human reviewer see when they open the appeal queue?

Any user can submit an appeal with the only criteria being that they provide the content-id of the entry they would like to appeal. The user must appeal using valid information, if an invalid content ID or the appeal reasoning is blank it will reject the appeal to then alert the user and ask them to try again with the correct information. When an appeal is submitted, it will mark the entry as under-review within the audit log and the reasoning for appealing is stored within the audit log for later stages. When a human reviewer opens the appeal queue they will see the content-ID belonging to the entry where the status will be under review, and the reasoning for the appeal will be present.

************************************************************************************************************************************
Anticipated edge cases: What types of content will your system handle poorly? Name at least two specific scenarios — not generic risks like "inaccurate detection," but specific cases like "a poem with heavy use of repetition and simple vocabulary that your heuristics might score as AI-generated."

Much like the example provided, a song more likely within the rap genre often relies on repetition within the bridges, a consistent sentence length, and a reoccuring vocabulary meant for stylistic reasons. This can be observed in songs like "Gucci Gang" by Lil Pump or "Around the World" by Daft Punk where everything measured in Signal 1 remains consistent, heavily implying that it's AI-generated although it was created by a human. AI-generated can be altered heavily by a human or prompted to be human-like by prompting or editing in informal grammer, punctuation mistakes also possibly changes sentence structure, synonyms, and spelling mistakes that intentionally makes the text appear more human within Signal 2 and slightly in Signal 1. As a result, the system will assign it a lower AI confidence score although a majority of the text was generated through AI. I also see the Ai model misclassifying a users' human input as AI if it is well written with a variety of vocabulary and correct usage of grammer since there is an implicit expectation from the model and from people that LLM models are much more likely to produce work that is grammatically correct. 


##Architecture

Diagram:

====================================================================
    Initial Submission Flow: ()
====================================================================
                Text + Content ID
                     |
                     ▼
                Post /Submit
                     |
                     ▼
                input: text
                     |
                Stylometric Evaluation (Signal 1)
                     |
                output: Stylometric Scoring (0-0.10)
                     |
                     ▼     
                input: text
                     |
                LLM Evaluation (Signal 2)
                     |
                output: LLM scoring (0-1.00)
                     |
                     ▼
                Confidence Scoring: Signal 2 * 0.90 + Signal 1
                     |
                     ▼
                Output: Confidence Score
                     |
                     ▼
                Transperancy Label Function
                     |
                     ▼
                output: label, attribution
                     |
                Logging timestamp, confidence score, label attribution into an audit
                     |
                     ▼
                JSON Response: Confidence Score, Label, and Attribution
                     |
                     ▼
                    User

====================================================================
    Appeal Submission Flow:
====================================================================
                Text(reasoning) + Content ID
                     |
                     ▼
                Post /appeal
                     |
                     ▼
                Find Audit Entry in DB belonging to the Content ID
                     |
                     ▼     
                Update status to under review
                     |
                Update reasoning with the reasoning from the user for the appeal
                     |
                     ▼ 
                JSON Response Confirming the Appeal Decision


## AI Tool Plan

M3 (submission endpoint + first signal): Which spec sections you'll provide to the AI tool (hint: your detection signals section + the diagram), what you'll ask it to generate (Flask app skeleton + the first signal function), and how you'll verify the output (test with a few inputs directly before wiring into the endpoint).

I will provide the OpenAI's Chatgpt with the Project Summary, Architecture, and Detection Signal portion of the spec to provide it context for it to work with while asking it to generate a Flask app skeleton that I can base entire pipeline on along with ideas for implimentations for Signal 1. I will verify this output by comparing it with the pipeline present in the lab and by testing a couple inputs to see that the Signal 1 is returning accurate responses.


M4 (second signal + confidence scoring): Which spec sections you'll provide (detection signals + uncertainty representation + diagram), what you'll ask for (second signal function + scoring logic), and what you'll check (do scores vary meaningfully between clearly AI and clearly human text?).

I will utilize Chatgpt provided by OpenAI to prompt it to give me guidance or points of contention within my prompt so I can then enforce a framework on llama when it generates numerical values,
this is immensely valuable because there is the only way to find out whether an LLM model will understand something for certain is by asking it and asking it to clarify points of confusion. Since it is also an LLM, I will prompt it to provide possible examples where it would be confused so I can verify these examples or benchmark my own implimentation. I'll provide it the architecture, Signal 2 definition, and the project summary so it can have the most context to assist me with. I'll verify this output by analyzing whether the examples are well defined enough to be utilize. In addition to this, I will prompt it to provide the code neccessary to ask llama for a specific JSON format that I can then parse to receive the score and explanation I desire.
After this is implimented, I will verify various outputs by changing out different system prompts with different design decisions in play based on the insights provided by the LLM to see the best outputs and parse to see if the JSON format is consistently provided.

M5 (production layer): Which spec sections you'll provide (label variants + appeals workflow + diagram), what you'll ask for (label generation logic + the /appeal endpoint), and how you'll verify (test all three label variants are reachable and that an appeal updates status correctly).

I will provide OpenAI's Chatgpt with the entire spec, the design decisions agreed upon on earlier stages, and some beta stages for programming to then ask it to verify whether my logic is correct and if there are any areas for improvement. I'll verify my final working code with different inputs and verify whether a 50/50 AI-Human created text is uncertain, a 100 AI-generated text, and human written text are correctly identified. I will then engage with the two different workflows by submitting input and then appealing it afterwards to determine if it's funcional or not.