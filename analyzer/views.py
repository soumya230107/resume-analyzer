import os
import json
import pdfplumber
import markdown
from google import genai
from django.shortcuts import render
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Extract text from PDF
def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

def analyze_with_gemini(resume_text, job_description):
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY is missing. Please set it in your .env file."}
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        Act as an expert Technical Recruiter and Resume Analyzer.
        I will provide you with a Resume Text and a Job Description. 
        Analyze the resume against the job description and output a JSON format response.
        
        Resume:
        {resume_text}
        
        Job Description:
        {job_description}
        
        Make sure to return *ONLY* valid JSON. Do not include markdown formatting like ```json.
        The JSON must strictly conform to this structure:
        {{
            "score": <a number between 0 and 100 representing the match score>,
            "strengths": ["list", "of", "candidate strengths matching the JD"],
            "missing_topics": ["list", "of", "missing skills, tools, or experiences requested in JD"],
            "job_suggestions": [
                {{
                    "title": "Job Title",
                    "reason": "Brief reason why it's a good fit based on the resume"
                }}
            ]
        }}
        """
        
        models_to_try = ['gemini-1.5-flash', 'gemini-2.5-flash', 'gemini-1.5-pro']
        text_resp = None
        last_err = None
        
        for _ in range(3): # 3 total retry loops
            for model_name in models_to_try:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    text_resp = response.text.strip()
                    break # Success with this model
                except Exception as e:
                    last_err = e
                    import time
                    time.sleep(1) # Brief pause before trying next model
            
            if text_resp:
                break # Found a valid response
            
            import time
            time.sleep(2) # Wait before restarting the model retry loop
            
        if not text_resp:
            raise Exception(f"API calls failed across multiple models. Last error: {str(last_err)}")
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
        text_resp = text_resp.strip()
            
        data = json.loads(text_resp)
        return data
    except Exception as e:
        return {"error": f"Failed to analyze with Gemini: {str(e)}"}

# Main view
def upload_resume(request):
    if request.method == "POST":
        resume_file = request.FILES.get("resume")
        job_description = request.POST.get("job_description")

        if not resume_file:
            return render(request, "upload.html", {"error": "Please upload a resume."})
        
        if not job_description:
            return render(request, "upload.html", {"error": "Please provide a job description."})
        
        # Extract text
        resume_text = extract_text_from_pdf(resume_file)

        # Gemini Analysis
        analysis_data = analyze_with_gemini(resume_text, job_description)

        if "error" in analysis_data:
            return render(request, "upload.html", {"error": analysis_data["error"]})
        
        return render(request, "result.html", {
            "score": analysis_data.get("score", 0),
            "strengths": analysis_data.get("strengths", []),
            "missing": analysis_data.get("missing_topics", []),
            "suggestions": analysis_data.get("job_suggestions", [])
        })

    return render(request, "upload.html")
