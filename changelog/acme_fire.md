# Changelog for acme_fire

- **company_name**
  - Old: `""`
  - New: `"the onboarding call for Acme Fire & Safety"`
- **business_hours**
  - Old: `{"days": ["Mon", "Fri"], "start": "08:00", "end": "17:00", "timezone": "America/Los_Angeles"}`
  - New: `{"days": [], "start": "", "end": "", "timezone": ""}`
- **emergency_routing_rules**
  - Old: `{"primary": [], "fallback": [], "notes": ""}`
  - New: `{"primary": [], "fallback": ["branch_manager"], "notes": ""}`
- **integration_constraints**
  - Old: `[]`
  - New: `["This is the onboarding call for Acme Fire & Safety. After hours, emergencies go to the on-call technician first, then the branch manager if they don't pick up."]`
- **questions_or_unknowns**
  - Old: `["Company name not clearly stated.", "Office address missing.", "Emergency definition unclear."]`
  - New: `["Business hours incomplete or missing.", "Office address missing.", "Services supported not clearly listed.", "Emergency definition unclear."]`
