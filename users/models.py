from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    
    person_id = models.CharField(max_length=50, unique=True)
    lastname_en = models.CharField(max_length=100, blank=True, null=True)
    firstname_en = models.CharField(max_length=100, blank=True, null=True)
    patronymic = models.CharField(max_length=100, blank=True, null=True)
    patronymic_en = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    birthdate = models.CharField(max_length=20, blank=True, null=True)
    
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    course_number = models.IntegerField(null=True, blank=True)
    city = models.CharField(max_length=200, blank=True)
    living_address = models.CharField(max_length=500, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.person_id})"


class EducationInfo(models.Model):
    student = models.OneToOneField(StudentProfile, on_delete=models.CASCADE, related_name='education')
    
    profession = models.CharField(max_length=300, blank=True)
    degree = models.CharField(max_length=100, blank=True)
    qualification = models.CharField(max_length=300, blank=True)
    specialization = models.CharField(max_length=300, blank=True)
    group_name = models.CharField(max_length=100, blank=True)
    adviser_full_name = models.CharField(max_length=200, blank=True)
    education_program_form = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.specialization}"


class AcademicRecord(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='academic_records')
    
    subject_name = models.CharField(max_length=500)
    credits = models.IntegerField()
    grade = models.CharField(max_length=10, null=True, blank=True)  # A, B+, C и т.д.
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-score']
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject_name} ({self.grade})"


class PracticeExperience(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='practices')
    
    organization = models.CharField(max_length=500, blank=True, null=True)
    position = models.CharField(max_length=300, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    practice_type = models.CharField(max_length=300, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.practice_type}"