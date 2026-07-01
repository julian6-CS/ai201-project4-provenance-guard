import uuid
from flask import Flask, request, jsonify

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from collections import Counter
from math import log
import sqlite3
from datetime import datetime, timezone
import os
from groq import Groq
import json
from dotenv import load_dotenv

DB_PATH = "audit_log.db"




def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
                    content_id TEXT PRIMARY KEY,
                    creator_id TEXT,
                    timestamp TEXT,
                    attribution TEXT,
                    attribution_score REAL,
                    signal1 REAL,
                    signal2 REAL,
                    confidence REAL,
                    status TEXT,
                    appeal_reasoning TEXT
                     )
                    """)

def log_event(entry):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO audit_log (
                content_id,
                creator_id,
                timestamp,
                attribution,
                attribution_score,
                signal1,
                signal2,
                confidence,
                status,
                appeal_reasoning
            )
            VALUES (
                :content_id,
                :creator_id,
                :timestamp,
                :attribution,
                :attribution_score,
                :signal1,
                :signal2,
                :confidence,
                :status,
                :appeal_reasoning
            )
        """, {
            **entry,
            "timestamp": datetime.now(timezone.utc).isoformat(),})
        

def read_log(limit=20):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]

def get_event(content_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute (
            "SELECT * FROM audit_log WHERE content_id = ?",
            (content_id,),).fetchone()
        return dict(row) if row else None

def create_log_entry():
    return {
        "content_id": "",
        "creator_id": "",
        "attribution": "",
        "attribution_score": 0.0,
        "signal1" : 0.0,
        "signal2" : 0.0,
        "confidence": 0.0,
        "status": "",
        "appeal_reasoning": "",
    }

def log_appeal(content_id, creator_reasoning):
    with sqlite3.connect(DB_PATH) as conn:
        success = conn.execute("""
            UPDATE audit_log SET status = ?, appeal_reasoning = ? WHERE content_id = ?""", ("under_review",creator_reasoning,content_id))

        return success.rowcount > 0

        """
            return (" SUCCESS: An Appeal has been placed and a moderator will soon review your case, for the meantime, the status of your case has been set to 'under review' ")
        else:
            return ("ERROR: Case could not be found, please provide an accurate content_ID")  """   

def stylometry_verification(text):

    string_lengths = [len(entry.strip()) for entry in text.split(".") if entry.strip()]
    unique_str_lengths = len(set(string_lengths))
    original_string_length_scoring = 0.52 * (1 - (unique_str_lengths / len(string_lengths)))

    punct_score = 0 # 0-1, closer to 0 meaning that the use of punctuation is very skewed towards a few while values closer to 1 has a even usage distribution between every possible punctuation mark
    common_punctuation = [".", ",", "?", "!", "'", "\"", ":", ";", "-"]
    punct_counts = Counter(c for c in text if c in common_punctuation)
    punct_total = sum(punct_counts.values())

    if punct_total == 0:
        punct_score = 0
    else:
        punc_probs = [c / punct_total for c in punct_counts.values()]
        statistical_diversity = -sum([p * log(p) for p in punc_probs])
        maximum_entropy = log(len(punc_probs))
        normalize_value = maximum_entropy if maximum_entropy > 1 else 1
        punct_score = statistical_diversity / normalize_value
    #if the entries are all equally diverse within the text, the close the punct score is to 1. Since AI is known to use punctuation evenly with a wider range while humans usually skew their usage towards a handful of punctuation marks

    word_diversity = 0
    stopwords = {"the","and","is","in","to","a","of","that","it","on","for"}

    words = [w.lower() for w in text.split() if w.lower() not in stopwords]
    word_count = Counter(words)
    word_total = sum(word_count.values())
    

    if word_total == 0:
        word_diversity = 0
    else:
        word_probs = [c / word_total for c in word_count.values()]
        starting_entropy = - sum(p * log(p) for p in word_probs)
        max_word_entropy = log(len(word_probs))
        normalization_value = max_word_entropy if max_word_entropy > 1 else 1
        word_diversity = starting_entropy / normalization_value


    stylometry_measurement = original_string_length_scoring + (0.24 * punct_score) + (0.24 * word_diversity)

    return stylometry_measurement

    #do a couple changes here to make this more stable


def scoring_against_llm(text):

    system_prompt = """
    You are a highly researched and successful AI evaluator. Your task is to estimate how strongly the writing provided resembles writing commonly produced by modern large language models.
    You will then produce the probability that this text was generated using a large language model with values ranging from [0.0 - 1.0]. Where 0.0 - 0.2 exhibits strong evidence of human writing, 0.2-0.4 is some AI-like characteristics but likely created by a human, 0.4-0.6 is uncertain regarding the origin of the text, 0.6-0.8 it contains a some characteristics associate with AI-generated writing, 0.8-1.0 is very strong evidence or reasoning that it was AI-generated

    
    You will make a holistic judgement while analyzing the semantic coherence, consistency of tone, discourse flow between sentences, predictable phrasing, use of formulaic language, whether the text is unusually balanced, linguistic patterns often seen in AI generated content, the use of generic or broad applicable statements, or use of phrasing associated with work produce by large language models

    DO NOT classify text as AI-generated solely because it is grammatically correct, formal, well-organized, or uses advanced vocabulary

    You will also provide your reasoning behind the scoring you provide

    YOU MUST return a JSON object in the following format,
        {
            "scoring": int or null,
            "reasoning": str or null
        
        }
    Where the scoring is a percentage of high likely the text was AI generated from 0 - 1.0. Reasoning is your reasoning why you gave it the score you gave it.

    Here is the input you will be evaluating,
    Text:
    """

    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    groq_client = Groq(api_key=api_key)

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages= [
            {
                "role":"system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content":text
            }
        ],
        response_format={"type": "json_object"}
    )

    parsed_query = json.loads(response.choices[0].message.content)

    if parsed_query.get("scoring") == None:
        return None
    else:
        return float(parsed_query["scoring"])



app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

init_db()


@app.route("/")
def home():
    return "Provenance Guard is running."


@app.route("/submit", methods=["POST"])
@limiter.limit("30 per minute; 240 per day")
def submit():
    data = request.get_json()
    text = data.get("text")
    creator_id = data.get("creator_id")

    if text is None or len(text) == 0:
        return jsonify({
        "content_id": "xxxxxxx",
        "attribution": "ERROR",
        "confidence": 0.0,
        "label": "Please provide valid text to verify",
        })

    content_id = str(uuid.uuid4())
    current_event = create_log_entry()
    current_event["content_id"] = content_id
    current_event["creator_id"] = creator_id

    llm_weight = 0.90
    stylometry_weight = 0.10

    org_signal_1 = stylometry_verification(text)
    org_signal_2 = scoring_against_llm(text)
    signal_1 = stylometry_weight * org_signal_1
    signal_2 = llm_weight * org_signal_2
    attribution_score = signal_1 + signal_2
    attribution = ""
    confidence_score = 0.0
    label = ""

    
    print(attribution_score)
    print(signal_1)
    print(signal_2)

    human_written_upper_lim = 0.45
    uncertain_upper_lim = 0.60

    
    uncertain_radius = (uncertain_upper_lim - human_written_upper_lim) / 2
    uncertain_center = (human_written_upper_lim + uncertain_radius)

    if 0.0 <= attribution_score <= human_written_upper_lim:
        confidence_score = (0.5 + 0.5 * (1 - (attribution_score / human_written_upper_lim)))
        attribution = "Human-Written"
        label = "There is a high confidence that this text was written by a human with no visible influence from AI."

    elif human_written_upper_lim < attribution_score <= uncertain_upper_lim:
        confidence_score = (1.0 - 0.5 * (abs(attribution_score - uncertain_center) / uncertain_radius))
        attribution = "Uncertain"
        label = "The system cannot confidently classify whether this text was written by a human or generated by an AI model."

    elif uncertain_upper_lim < attribution_score <= 1.0:
        confidence_score = (0.5 + 0.5 * ((attribution_score - uncertain_upper_lim) / (1.0 - uncertain_upper_lim)))
        attribution = "AI-Generated"
        label = "The system has high confidence that the provided text was generated by an AI model."

    else:
        raise ValueError(
            f"Invalid attribution score: {attribution_score}. Expected a value between 0.0 and 1.0."
        )

    current_event["attribution"] = attribution
    current_event["attribution_score"] = attribution_score
    current_event["signal1"] = org_signal_1
    current_event["signal2"] = org_signal_2
    current_event["confidence"] = confidence_score
    current_event["status"] = "classified"

    log_event(current_event)
    

    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "attribution_score" : attribution_score,
        "confidence": confidence_score,
        "label": label,
    })



@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json()
    content_id = data.get("content_id")
    reasoning = data.get("creator_reasoning")

    if content_id is None or content_id == 0 :
        return jsonify({
        "content_id": content_id,
        "status": "ERROR",
        "message": "Please provide an accurate content_id that corresponds to an entry",
    })


    if reasoning is None or len(reasoning) == 0:
        return jsonify({
        "content_id": content_id,
        "status": "ERROR",
        "message": "Please provide your reasoning for appealing, the moderation needs to understand your perspective to consider appealing",
    })

    appeal_success = log_appeal(content_id=content_id,creator_reasoning=reasoning)

    if appeal_success:
        return jsonify({
            "content_id": content_id,
            "status": "under_review",
            "message": "Your appeal was received and is under review.",
        })
    else:
        return jsonify({
        "content_id": content_id,
        "status": "ERROR",
        "message": "Please provide an accurate content_id that corresponds to an entry",
    })


@app.route("/log", methods=["GET"])
def view_log():
    return jsonify({"entries": read_log()})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
    # text_test = "U smelly potatoes"
    # with app.test_client() as client:
    #     response = client.post("/submit" , json = {
    #         "creator_id": "090394",
    #         "text" : text_test

    #     })
    #     print(response.json)