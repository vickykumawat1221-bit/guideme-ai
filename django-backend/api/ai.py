from sentence_transformers import SentenceTransformer, util

# Load model only once
model = SentenceTransformer("all-MiniLM-L6-v2")

def recommend_experts(question, experts):

    question_embedding = model.encode(question, convert_to_tensor=True)

    results = []

    for expert in experts:

        # Include more information about each expert
        expert_text = (
            f"{expert.profession} "
            f"{expert.languages} "
            f"{expert.experience} years "
            f"{expert.name}"
        )

        expert_embedding = model.encode(expert_text, convert_to_tensor=True)

        score = util.cos_sim(question_embedding, expert_embedding).item()

        results.append((score, expert))

    # Highest similarity first
    results.sort(key=lambda x: x[0], reverse=True)

    # Return only the top 5 experts
    return [expert for score, expert in results[:5]]