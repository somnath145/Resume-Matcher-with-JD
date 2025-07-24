from flask import Blueprint, render_template, request, url_for, flash, session, redirect
from app import db
from app.models import Resume, Users
from app.routes.form import ResumeUploadForm, JobDescriptionForm
from werkzeug.utils import secure_filename
from sentence_transformers import SentenceTransformer, util
from pdfminer.high_level import extract_text
import os

from pdfminer.high_level import extract_text
import re
from nltk.tokenize import sent_tokenize
import nltk
nltk.download('punkt')




task_bp = Blueprint('task', __name__)

@task_bp.route('/')
def home():
    return render_template('home.html')

@task_bp.route('/upload', methods=['GET', 'POST'])
def upload_resume():
    if 'username' not in session:
        return redirect(url_for('auth.login'))
    
    user = Users.query.filter_by(username = session.get('username')).first()
    if not user:
        flash("User not found in DB. Please login again.")
        return redirect(url_for('auth.login'))
    
    form = ResumeUploadForm()

    if form.validate_on_submit():
        file = form.resume.data
        new_resume = Resume(
            filename=secure_filename(file.filename),
            data=file.read(),
            user_id = user.id)
        
        db.session.add(new_resume)
        db.session.commit()
        flash('Resume uploaded successfully.')
        return redirect(url_for('task.upload_resume'))
    
    resumes = Resume.query.filter_by(user_id = user.id).all()

    return render_template('upload.html',resumes=resumes, form=form)

@task_bp.route('/delete/<int:resume_id>',methods=['POST'])
def delete_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)
    if resume:
        db.session.delete(resume)
        db.session.commit()
    return redirect(url_for('task.upload_resume'))
    
@task_bp.route('/analyze/<int:resume_id>', methods=['POST'])
def analyze_resume(resume_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    # === Load Resume ===
    resume = Resume.query.get_or_404(resume_id)
    form = JobDescriptionForm()

    temp_path = f"temp_{resume.filename}"
    with open(temp_path, "wb") as f:
        f.write(resume.data)

    resume_text = extract_text(temp_path)
    os.remove(temp_path)

    # === Clean Text Function ===
    def clean_text(text):
        text = re.sub(r"<.*?>", "", text)
        text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
        text = text.lower()
        return ' '.join(text.split())

    resume_text = clean_text(resume_text)

    if form.validate_on_submit():
        job_text = clean_text(form.job_description.data)

        # === Load Model ===
        model = SentenceTransformer('all-mpnet-base-v2')

        # === Sentence Chunking ===
        resume_chunks = sent_tokenize(resume_text)
        jd_chunks = sent_tokenize(job_text)

        resume_embeddings = model.encode(resume_chunks, convert_to_tensor=True)
        jd_embeddings = model.encode(jd_chunks, convert_to_tensor=True)

        cosine_scores = util.pytorch_cos_sim(resume_embeddings, jd_embeddings)
        top_k = 5
        top_scores = sorted([score.item() for score in cosine_scores.flatten()], reverse=True)[:top_k]
        avg_top_score = sum(top_scores) / len(top_scores)


        def extract_skills(text):
            # Read skills from file
            with open("app\skills.txt", "r", encoding="utf-8") as file:
                skill_list = [line.strip().lower() for line in file if line.strip()]

            found = set()
            for skill in skill_list:
                if skill in text.lower():
                    found.add(skill)
            return found

        resume_skills = extract_skills(resume_text)
        jd_skills = extract_skills(job_text)

        #find match and not match skills

        match_skills = []
        not_match_skills = []

        for skill in jd_skills:
            if skill in resume_skills:
                match_skills.append(skill)
            else:
                not_match_skills.append(skill)

        skill_score = len(resume_skills & jd_skills) / len(jd_skills) if (resume_skills | jd_skills) else 0

        # Combine both scores
        final_score = 0.20 * avg_top_score + 0.80 * skill_score
        # final_score =  skill_score
        match_percentage = round(final_score * 100, 2)

        #additional information part
        required_sections = ['education','experience','skills','projects','internship']
        found_section = [sec for sec in required_sections if sec in resume_text.lower()]

        import fitz # pyMuPDF

        #check image is present or not
        def Check_image_in_pdf(data):
            doc = fitz.open(stream=data, filetype = "pdf")
            for page in doc:
                if page.get_images():
                    return True
            return False
        
        #check font name
        def Check_font(data):
            doc = fitz.open(stream=data, filetype = "pdf")
            font_used = set()
            for page in doc:
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                font_used.add(span["font"])
            return font_used

        has_image = Check_image_in_pdf(resume.data)
        fonts = Check_font(resume.data)

        ats_report = {}

        ats_report["Section Found"] = found_section
        ats_report["Font"] = fonts
        if(has_image):
            ats_report["Has Image"] = "Yes"
        else:
            ats_report["Has Image"] = "No"

        if (len(found_section)<2 or has_image or len(fonts)>2):
            ats_report["ATS Friendly"] = "No"
        else:
            ats_report["ATS Friendly"] = "Yes"



        # Suggestion video of mismatched skills

        def load_youtube_links(filename = 'app/video_suggations.txt'):
            youtube_links = {}
            with open(filename, 'r', encoding='utf-8') as file:
                for line in file:
                    if ':' in line:
                        key, value = line.strip().split(':', 1)
                        youtube_links[key.strip().lower()] = value.strip()
            return youtube_links
        
        youtube_links = load_youtube_links()

        def suggest_link(not_match_skills, youtube_links):
            suggestions = {}
            for skill in not_match_skills:
                if skill.lower() in youtube_links:
                    suggestions[skill] = youtube_links[skill.lower()]
            return suggestions

        video_suggestion = suggest_link(not_match_skills, youtube_links)


        # Recommended Job Role

        import json

        with open('app/routes/jds.json', 'r', encoding='utf-8') as f:
            jds = json.load(f)

        resume_skills_text = ", ".join(resume_skills)
        skill_embedding = model.encode(resume_skills_text, convert_to_tensor=True) #if convert_to_tensor = False it will give a numpy array, which is not good for pytorch based cosine similarity
        recommendation = {}
        for jd in jds:
            job_embedding = model.encode(jd["description"],convert_to_tensor=True)
            similarity_score = util.pytorch_cos_sim(skill_embedding, job_embedding).item()
            recommendation[jd["role"]] = round(similarity_score * 100, 2)
            
        

        return render_template('result.html',match_percentage=match_percentage,
                    match_skills = match_skills , not_match_skills=not_match_skills, ats_report=ats_report, video_suggestion= video_suggestion,recommendation=recommendation)
    return render_template('match.html', form=form, resume=resume)


