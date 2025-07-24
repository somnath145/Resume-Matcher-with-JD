from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import InputRequired
from wtforms import SubmitField, TextAreaField

class ResumeUploadForm(FlaskForm):
    resume = FileField('Upload Your Resume (PDF)', validators=[InputRequired(), FileAllowed(['pdf'], 'PDFs only!')])
    submit = SubmitField('Upload')

class JobDescriptionForm(FlaskForm):
    job_description = TextAreaField('Past yor job description',validators=[InputRequired()])
    submit = SubmitField('Analyse')