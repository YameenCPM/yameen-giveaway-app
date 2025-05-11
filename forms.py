from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, DateTimeField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError
from datetime import datetime

class GiveawayEntryForm(FlaskForm):
    """Form for users to enter a giveaway"""
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    phone = StringField('Phone Number (optional)', validators=[Length(max=20)])
    submit = SubmitField('Enter Giveaway')

class AdminLoginForm(FlaskForm):
    """Form for admin login"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class GiveawayForm(FlaskForm):
    """Form for creating and editing giveaways"""
    title = StringField('Giveaway Title', validators=[DataRequired(), Length(min=5, max=100)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10)])
    prize = StringField('Prize', validators=[DataRequired(), Length(min=3, max=200)])
    image = FileField('Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    start_date = DateTimeField('Start Date (YYYY-MM-DD HH:MM)', format='%Y-%m-%d %H:%M', 
                              validators=[DataRequired()])
    end_date = DateTimeField('End Date (YYYY-MM-DD HH:MM)', format='%Y-%m-%d %H:%M', 
                            validators=[DataRequired()])
    submit = SubmitField('Save Giveaway')
    
    def validate_end_date(self, field):
        """Validate that end date is after start date"""
        if field.data <= self.start_date.data:
            raise ValidationError('End date must be after start date.')
            
        if field.data < datetime.now() and not self.is_edit:
            raise ValidationError('End date cannot be in the past.')
            
    @property
    def is_edit(self):
        """Check if this is an edit form"""
        return hasattr(self, '_obj') and self._obj is not None
