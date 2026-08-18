#!/usr/bin/env python3
"""
Workforces Persona Management Script
Provides dynamic persona listing, recommendation, creation, and export for workforces projects.
Stores personas in workforces/personas/ (or workforces/personas.json).
"""

import os
import sys
import json
import glob
import re
import argparse

DEFAULT_RECOMMENDATIONS = {
    "saas": {
        "author_voices": [
            {
                "id": "technical-architect",
                "name": "The Technical Architect / Systems Thinker",
                "type": "author_voice",
                "perspective": "Engineering rigor, scalability, reliability, telemetry metrics, and systems design.",
                "tone": "Authoritative, analytical, concise, data-backed",
                "platforms": ["x.com", "linkedin", "github", "hacker-news"],
                "keywords": ["architecture", "scale", "latency", "reliability", "infrastructure"]
            },
            {
                "id": "ai-enabler",
                "name": "The AI Enabler / Workflow Pragmatist",
                "type": "author_voice",
                "perspective": "Practical agentic orchestration, rapid prototyping, builder momentum, and workflow automation.",
                "tone": "Energetic, tactical, builder-friendly, insightful",
                "platforms": ["x.com", "skool", "linkedin"],
                "keywords": ["agents", "workflows", "automation", "leverage", "speed"]
            }
        ],
        "target_audiences": [
            {
                "id": "enterprise-decision-maker",
                "name": "Enterprise Tech Decision Maker",
                "type": "target_audience",
                "role": "VP of Engineering, CTO, Head of Infrastructure",
                "pain_points": ["Security compliance", "Team context switching", "Vendor lock-in", "High downtime risk"],
                "triggers": ["SOC2/HIPAA compliance", "SLAs", "Dedicated support", "Clear ROI"]
            },
            {
                "id": "startup-builder",
                "name": "Growth Startup Founder / Tech Lead",
                "type": "target_audience",
                "role": "Seed/Series A Founder, Solo Operator, Lead Engineer",
                "pain_points": ["Slow shipping velocity", "Hiring constraints", "Budget limits"],
                "triggers": ["Fast setup", "Transparent pricing", "Self-serve ease", "Open standards"]
            }
        ]
    },
    "local_service": {
        "author_voices": [
            {
                "id": "trusted-local-expert",
                "name": "The Trusted Local Authority",
                "type": "author_voice",
                "perspective": "Honest, reliable, community-rooted craftsmanship and transparent customer service.",
                "tone": "Warm, reassuring, straightforward, neighborly",
                "platforms": ["google-business", "facebook", "nextdoor", "instagram"],
                "keywords": ["reliable", "licensed", "guaranteed", "local", "transparent"]
            }
        ],
        "target_audiences": [
            {
                "id": "busy-homeowner",
                "name": "Busy Homeowner / Property Manager",
                "type": "target_audience",
                "role": "Homeowner, Residential Landlord",
                "pain_points": ["Unreliable contractors", "Hidden fees", "Slow quotes"],
                "triggers": ["Same-day response", "Upfront pricing", "5-star local reviews", "Satisfaction guarantee"]
            }
        ]
    },
    "agency": {
        "author_voices": [
            {
                "id": "growth-operator",
                "name": "The Growth Strategist / Operator",
                "type": "author_voice",
                "perspective": "High-leverage business scaling, conversion optimization, and client ROI.",
                "tone": "Sharp, pragmatic, results-oriented, strategic",
                "platforms": ["linkedin", "x.com", "skool"],
                "keywords": ["funnels", "conversion", "retention", "CAC", "LTV"]
            }
        ],
        "target_audiences": [
            {
                "id": "marketing-director",
                "name": "Director of Marketing / CMO",
                "type": "target_audience",
                "role": "Marketing Director at mid-market brand",
                "pain_points": ["Stagnant pipeline", "Overwhelmed internal team", "Unclear agency reporting"],
                "triggers": ["Provable case studies", "Turnkey execution", "Transparent weekly dashboards"]
            }
        ]
    }
}

def get_personas_dir(target_dir):
    return os.path.join(os.path.abspath(target_dir), "workforces", "personas")

def get_personas_file(target_dir):
    return os.path.join(os.path.abspath(target_dir), "workforces", "personas.json")

def load_personas(target_dir):
    personas = []
    p_file = get_personas_file(target_dir)
    if os.path.exists(p_file):
        try:
            with open(p_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    personas.extend(data)
                elif isinstance(data, dict):
                    personas.extend(data.get("personas", []))
        except Exception:
            pass

    p_dir = get_personas_dir(target_dir)
    if os.path.isdir(p_dir):
        for fpath in glob.glob(os.path.join(p_dir, "*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    p = json.load(f)
                    if isinstance(p, dict) and "id" in p:
                        if not any(x.get("id") == p["id"] for x in personas):
                            personas.append(p)
            except Exception:
                pass

    return personas

def save_persona(target_dir, persona_data):
    p_dir = get_personas_dir(target_dir)
    os.makedirs(p_dir, exist_ok=True)
    p_id = persona_data.get("id", "custom-persona")
    fpath = os.path.join(p_dir, f"{p_id}.json")
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(persona_data, f, indent=2)
    return fpath

def detect_project_domain(target_dir):
    workrules_path = os.path.join(target_dir, "workforces", "workrules.md")
    if os.path.exists(workrules_path):
        with open(workrules_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().lower()
            if "local" in content or "service" in content:
                return "local_service"
            if "agency" in content or "client" in content:
                return "agency"
    return "saas"

def list_personas(target_dir):
    personas = load_personas(target_dir)
    if not personas:
        print("No dynamic personas found in workforces/personas/. Run --recommend to view suggestions or --create to add one.")
        return
    print(f"\n📋 Active Project Personas ({len(personas)} found):")
    print("=" * 60)
    for p in personas:
        p_type = p.get("type", "author_voice")
        type_badge = "🎙️ Author Voice" if p_type == "author_voice" else "🎯 Target Audience"
        print(f"\n• [{p.get('id')}] {p.get('name')} ({type_badge})")
        if p_type == "author_voice":
            print(f"  Perspective: {p.get('perspective', 'N/A')}")
            print(f"  Tone:        {p.get('tone', 'N/A')}")
            if p.get("platforms"):
                print(f"  Platforms:   {', '.join(p.get('platforms'))}")
        else:
            print(f"  Role:        {p.get('role', 'N/A')}")
            if p.get("pain_points"):
                print(f"  Pain Points: {', '.join(p.get('pain_points'))}")
            if p.get("triggers"):
                print(f"  Triggers:    {', '.join(p.get('triggers'))}")
    print("\n" + "=" * 60)

def recommend_personas(target_dir):
    domain = detect_project_domain(target_dir)
    rec = DEFAULT_RECOMMENDATIONS.get(domain, DEFAULT_RECOMMENDATIONS["saas"])
    print(f"\n💡 Recommended Personas for project domain [{domain}]:")
    print("=" * 60)
    print("\n--- 🎙️ Recommended Author / Voice Personas ---")
    for a in rec["author_voices"]:
        print(f"\n• ID: {a['id']}")
        print(f"  Name:        {a['name']}")
        print(f"  Perspective: {a['perspective']}")
        print(f"  Tone:        {a['tone']}")
        print(f"  Platforms:   {', '.join(a['platforms'])}")
    print("\n--- 🎯 Recommended Target Audience Personas ---")
    for t in rec["target_audiences"]:
        print(f"\n• ID: {t['id']}")
        print(f"  Name:        {t['name']}")
        print(f"  Role:        {t['role']}")
        print(f"  Pain Points: {', '.join(t['pain_points'])}")
        print(f"  Triggers:    {', '.join(t['triggers'])}")
    print("\n" + "=" * 60)
    print("To install a recommended persona, run: python3 manage_personas.py --create-from-recommendation <id>")

def export_context(target_dir):
    personas = load_personas(target_dir)
    if not personas:
        # Fallback to recommended
        domain = detect_project_domain(target_dir)
        rec = DEFAULT_RECOMMENDATIONS.get(domain, DEFAULT_RECOMMENDATIONS["saas"])
        personas = rec["author_voices"] + rec["target_audiences"]

    output = {
        "available_personas": personas,
        "author_voices": [p for p in personas if p.get("type") == "author_voice"],
        "target_audiences": [p for p in personas if p.get("type") == "target_audience"]
    }
    print(json.dumps(output, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Workforces Persona Engine")
    parser.add_argument("--target", default=".", help="Root of project workspace")
    parser.add_argument("--list", action="store_true", help="List active project personas")
    parser.add_argument("--recommend", action="store_true", help="Recommend domain personas")
    parser.add_argument("--export-context", action="store_true", help="Output JSON context for agents")
    parser.add_argument("--create-from-recommendation", help="Install a recommended persona by ID")
    parser.add_argument("--add-json", help="Add persona from raw JSON string")

    args = parser.parse_args()

    if args.list:
        list_personas(args.target)
    elif args.recommend:
        recommend_personas(args.target)
    elif args.export_context:
        export_context(args.target)
    elif args.create_from_recommendation:
        domain = detect_project_domain(args.target)
        rec = DEFAULT_RECOMMENDATIONS.get(domain, DEFAULT_RECOMMENDATIONS["saas"])
        all_recs = rec["author_voices"] + rec["target_audiences"]
        match = next((p for p in all_recs if p["id"] == args.create_from_recommendation), None)
        if match:
            path = save_persona(args.target, match)
            print(f"✓ Saved persona [{match['id']}] to {path}")
        else:
            print(f"Error: Recommendation ID '{args.create_from_recommendation}' not found.")
    elif args.add_json:
        try:
            data = json.loads(args.add_json)
            path = save_persona(args.target, data)
            print(f"✓ Saved persona [{data.get('id')}] to {path}")
        except Exception as e:
            print(f"Error parsing persona JSON: {e}")
    else:
        list_personas(args.target)

if __name__ == "__main__":
    main()
