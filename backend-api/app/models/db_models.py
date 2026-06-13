import logging
from app.core.database import SQLALCHEMY_AVAILABLE

logger = logging.getLogger(__name__)

if SQLALCHEMY_AVAILABLE:
    from sqlalchemy import Column, Integer, String, Float, Text, DateTime
    from sqlalchemy.sql import func
    from app.core.database import Base

    class IncidentDiagnosis(Base):
        __tablename__ = "incident_diagnoses"

        id = Column(Integer, primary_key=True, index=True)
        service_name = Column(String, index=True)
        timestamp = Column(DateTime(timezone=True), server_default=func.now())
        pod_status = Column(Text)  # Store JSON representation as text
        log_analysis = Column(Text)
        metrics_analysis = Column(Text)
        runbook_matched = Column(String)  # 'True' / 'False' string serialization
        root_cause = Column(Text)
        recommendations = Column(Text)
        confidence_score = Column(Float)
        
        def to_dict(self):
            import json
            try:
                pods_data = json.loads(self.pod_status)
            except Exception:
                pods_data = self.pod_status
                
            return {
                "id": self.id,
                "service_name": self.service_name,
                "timestamp": self.timestamp.isoformat() if self.timestamp else None,
                "pod_status": pods_data,
                "log_analysis": self.log_analysis,
                "metrics_analysis": self.metrics_analysis,
                "runbook_matched": self.runbook_matched == "True",
                "root_cause": self.root_cause,
                "recommendations": self.recommendations,
                "confidence_score": self.confidence_score
            }
else:
    class IncidentDiagnosis:
        def to_dict(self):
            return {}
