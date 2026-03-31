
import os
import google.generativeai as genai

# DO NOT HARDCODE KEY IN FINAL VERSION
os.environ["GOOGLE_API_KEY"] = "AIzaSyAnsO2yoVd-b3C9KQ67OCCi99RpsHjXlJA"

def test_api():
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    # Testing models
    models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"]
    
    for model_name in models_to_try:
        print(f"Testing model: {model_name}...")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Hello, respond with 'OK' if you are working.")
            print(f"Result for {model_name}: {response.text.strip()}")
            return model_name
        except Exception as e:
            print(f"Failed for {model_name}: {e}")
    return None

if __name__ == "__main__":
    working_model = test_api()
    if working_model:
        print(f"\nSUCCESS: Use {working_model}")
    else:
        print("\nFAILURE: No working model found with this key.")
