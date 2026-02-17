from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .db import Base

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(64), index=True)
    email = Column(String(256), index=True)
    full_name = Column(String(256), index=True)
    id_number_hash = Column(String(128), index=True)
    location_city = Column(String(128), index=True)
    raw_paragraph = Column(Text)
    cv_text = Column(Text)

    experiences = relationship("Experience", back_populates="candidate", cascade="all, delete-orphan")
    education = relationship("Education", back_populates="candidate", cascade="all, delete-orphan")


class Education(Base):
    __tablename__ = "education"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), index=True)
    institution = Column(String(256), index=True)
    degree = Column(String(256), index=True)
    major = Column(String(256), index=True)
    gpa = Column(String(64), index=True)
    status = Column(String(32), index=True)
    expected_graduation_date = Column(String(64), index=True)

    candidate = relationship("Candidate", back_populates="education")

class Experience(Base):
    __tablename__ = "experiences"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), index=True)
    company = Column(String(256), index=True)
    title = Column(String(256), index=True)
    dates = Column(String(128), index=True)
    employment_status = Column(String(32), index=True)
    description = Column(Text)

    candidate = relationship("Candidate", back_populates="experiences")
