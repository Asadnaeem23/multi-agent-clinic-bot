import os
from sqlalchemy.orm import Session
from database import BusinessSettings

DEFAULT_BUSINESS_CONTEXT = """Business: Bright Smile Dental Clinic

About Us:
Bright Smile Dental Clinic is a modern, patient-focused dental clinic dedicated to providing high-quality dental care in Pakistan. With over 15 years of experience, we offer affordable, reliable, and comfortable dental treatments for patients of all ages using modern equipment and the latest techniques.

Our Services:

1. General Dentistry
- Dental Consultation (PKR 2,000)
- Routine Check-up & Scaling (PKR 4,000 - 7,000)
- Tooth Filling (PKR 3,500 - 8,000)
- Root Canal Treatment (PKR 15,000 - 35,000)
- Tooth Extraction (PKR 4,000 - 12,000)

2. Cosmetic Dentistry
- Teeth Whitening (PKR 18,000 - 35,000)
- Dental Veneers (PKR 25,000 - 60,000 per tooth)
- Dental Bonding (PKR 8,000 - 20,000)

3. Orthodontics
- Metal Braces (PKR 180,000 - 350,000)
- Ceramic Braces (PKR 220,000 - 400,000)
- Clear Aligners (PKR 250,000 - 500,000)
- Retainers (PKR 15,000 - 35,000)

4. Dental Implants
- Dental Implant Consultation
- Single Tooth Implant (PKR 120,000 - 250,000)
- Implant Crown

5. Pediatric Dentistry
- Children's Dental Check-up
- Fluoride Treatment
- Sealants
- Tooth-Colored Fillings

6. Emergency Dental Care
- Same-day emergency appointments (subject to availability)
- Severe Toothache Treatment
- Broken Tooth Repair
- Emergency Tooth Extraction
- Swelling & Infection Management

Our Doctors:
1. Dr. Ahmed Khan - General & Restorative Dentist (15+ years experience)
2. Dr. Ayesha Malik - Cosmetic Dentist (10+ years experience)
3. Dr. Hassan Ali - Orthodontist (12+ years experience)

Business Hours:
Monday - Saturday: 10:00 AM - 8:00 PM
Sunday: Closed

Location:
MM Alam Road,
Gulberg III,
Lahore, Punjab, Pakistan

Contact:
Phone: +92 300 1234567
WhatsApp: +92 300 1234567
Email: info@brightsmiledental.pk

Accepted Payments:
- Cash
- Debit/Credit Cards
- JazzCash
- Easypaisa
- Bank Transfer

Insurance:
We assist patients with reimbursement documentation for insurance providers where applicable. Please contact the clinic to confirm your insurance eligibility.

Appointment Policy:
- Appointments are recommended but walk-ins are welcome depending on availability.
- Patients should arrive 10–15 minutes before their scheduled appointment.
- Please inform the clinic at least 24 hours in advance if you need to cancel or reschedule.

Emergency Policy:
Emergency patients are accommodated on priority whenever possible. Please call the clinic before visiting.

Languages Spoken:
- English
- Urdu
- Punjabi

Why Choose Bright Smile Dental Clinic?
- Experienced and qualified dentists
- Modern digital dental equipment
- Sterilized instruments following international standards
- Affordable treatment plans
- Friendly and compassionate staff
- Comfortable waiting area
- Personalized treatment plans
- Digital patient records
- Online appointment booking
- WhatsApp support for inquiries and appointments
"""

def get_business_context(db: Session) -> str:
    """Get business context from database or return default"""
    context_setting = db.query(BusinessSettings).filter(BusinessSettings.key == "business_context").first()
    if context_setting:
        return context_setting.value
    return DEFAULT_BUSINESS_CONTEXT

def update_business_context(db: Session, new_context: str):
    """Update business context in database"""
    context_setting = db.query(BusinessSettings).filter(BusinessSettings.key == "business_context").first()
    if context_setting:
        context_setting.value = new_context
    else:
        context_setting = BusinessSettings(key="business_context", value=new_context)
        db.add(context_setting)
    db.commit()
    return context_setting
