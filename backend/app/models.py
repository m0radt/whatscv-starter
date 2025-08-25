from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .db import Base

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(64), index=True)
    full_name = Column(String(256), index=True)
    id_number_hash = Column(String(128), index=True)
    education_institution = Column(String(256), index=True)
    education_level = Column(String(128), index=True)
    year_of_study = Column(String(64), index=True)
    location_city = Column(String(128), index=True)
    raw_paragraph = Column(Text)
    cv_text = Column(Text)

    experiences = relationship("Experience", back_populates="candidate", cascade="all, delete-orphan")

class Experience(Base):
    __tablename__ = "experiences"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), index=True)
    company = Column(String(256), index=True)
    title = Column(String(256), index=True)
    start = Column(String(64), index=True)
    end = Column(String(64), index=True)
    description = Column(Text)

    candidate = relationship("Candidate", back_populates="experiences")