# Changelog for bens_electric

- **business_hours**
  - Old: `{"days": [], "start": "30:00", "end": "08:00", "timezone": ""}`
  - New: `{"days": ["Mon", "Fri"], "start": "12:00", "end": "03:00", "timezone": "America/New_York"}`
- **emergency_definition**
  - Old: `[]`
  - New: `["After-hours emergency handling: There is no general after-hours emergency service except for one key property manager client. Calls from this client can be patched through to Ben directly for emergencies. Pawan will configure Clara to recognize this client and allow call patching only for them. Ben to provide detailed client info including customer name, property name, address, and primary contact for after-hours emergencies. This client manages about 20 gas station properties requiring occasional emergency service."]`
- **emergency_routing_rules**
  - Old: `{"primary": [], "fallback": [], "notes": ""}`
  - New: `{"primary": [], "fallback": ["branch_manager"], "notes": ""}`
- **non_emergency_routing_rules**
  - Old: `{"primary": ["front_desk"], "fallback": [], "notes": ""}`
  - New: `{"primary": [], "fallback": [], "notes": ""}`
- **integration_constraints**
  - Old: `[]`
  - New: `["Integration: Jobber integration is in progress. Onboarding team will tailor Clara's functionalities to Ben's business needs and workflows. Never create jobs or work orders in Jobber or other systems without confirmation from dispatch or Ben."]`
- **questions_or_unknowns**
  - Old: `["Business hours incomplete or missing.", "Office address missing.", "Emergency definition unclear."]`
  - New: `["Office address missing."]`
