#!/usr/bin/env python3
"""
Test Suite for Social Engagement Engine & Progressive Crawler
Validates intent detection, thread unfolding, newcomer welcome generation,
developer/AWS advice generation, SQLite indexing, and dashboard rendering.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

# Import local engine modules
sys.path.insert(0, os.path.dirname(__file__))
from social_crawler import (
    detect_post_intent,
    extract_thread_comments_as_individual_posts,
    parse_raw_text_stream,
)
from engagement_evaluator import (
    calculate_relevance_and_virality,
    generate_op_response,
    load_config,
    process_post_item,
    resolve_persona_for_post,
)
from social_indexer import (
    export_to_json,
    get_db_path,
    init_db,
    is_post_cold,
    upsert_draft_reply,
    upsert_post,
)
from dashboard_generator import generate_dashboard, render_post_card


class TestSocialEngine(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_social_")
        self.social_dir = os.path.join(self.test_dir, "workforces", "social")
        os.makedirs(os.path.join(self.social_dir, "personas"), exist_ok=True)
        self.db_path = os.path.join(self.social_dir, "social_index.db")
        init_db(self.db_path)

        # Mock config
        self.config = {
            "goals": {
                "primary": "community_growth",
                "target_audiences": ["AI engineers", "SaaS founders", "developers"]
            },
            "platforms": {
                "skool_com": {
                    "enabled": True,
                    "keywords": ["architecture", "scaling", "aws", "agents"],
                    "min_engagement_threshold": {"likes": 2, "replies": 1},
                    "persona": "skool-community-mentor"
                }
            }
        }
        with open(os.path.join(self.social_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(self.config, f)

        # Mock persona
        self.persona = {
            "id": "skool-community-mentor",
            "name": "Community Mentor Lead",
            "domain": "Software Engineering & Multi-Agent Systems",
            "platform": "skool.com",
            "response_frameworks": {
                "value_points": [
                    "Separating transient turn notes from persistent OKF catalogs",
                    "Using automated post-tool validation hooks to catch broken links",
                    "Decoupling planning from code execution to prevent cognitive drift"
                ],
                "catalyst_questions": [
                    "What is the primary architecture or automation workflow you're looking to build first?"
                ]
            }
        }
        with open(os.path.join(self.social_dir, "personas", "skool-community-mentor.json"), "w", encoding="utf-8") as f:
            json.dump(self.persona, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_intent_detection(self):
        # 1. Newcomer introduction test
        intro_text = "Hey everyone! Just joined the group. My background is in fullstack development and building automations."
        intent_intro = detect_post_intent(intro_text, "Welcome! Intro yourself")
        self.assertTrue(intent_intro["is_introduction"])

        # 2. Developer / AWS bottleneck test
        tech_text = "Having an issue with AWS Lambda timing out during our Amplify deployment pipeline when processing large payloads."
        intent_tech = detect_post_intent(tech_text, "Amplify Gen 2 Lambda Timeout")
        self.assertTrue(intent_tech["is_tech_bottleneck"])

        # 3. Standard question test
        q_text = "How do you handle rate limits across multi-agent workflows?"
        intent_q = detect_post_intent(q_text, "Rate limiting strategies")
        self.assertTrue(intent_q["is_question"])

    def test_thread_unfolding_into_individual_member_posts(self):
        thread_data = {
            "platform": "skool.com",
            "community": "ai-automation-vault",
            "url": "https://www.skool.com/ai-automation-vault/welcome-intro-yourself",
            "title": "🎉 Welcome! Intro yourself...",
            "sub_comments": [
                {
                    "author_name": "Marcus Vance",
                    "commenter_handle": "@marcusv",
                    "comment_text": "Hey everyone, I run a boutique automation agency in London. Excited to dive into multi-agent systems.",
                    "likes": 2
                },
                {
                    "author_name": "Elena Rostova",
                    "commenter_handle": "@elena_ai",
                    "comment_text": "Hello! I am a backend engineer transitioning into autonomous agents. Currently exploring AWS serverless setups.",
                    "likes": 3
                }
            ]
        }

        unfolded = extract_thread_comments_as_individual_posts(thread_data, parent_title=thread_data["title"])
        self.assertEqual(len(unfolded), 2)
        self.assertEqual(unfolded[0]["author"], "Marcus Vance")
        self.assertTrue(unfolded[0]["is_introduction"])
        self.assertEqual(unfolded[1]["author"], "Elena Rostova")
        self.assertTrue(unfolded[1]["is_tech_bottleneck"])

    def test_relevance_scoring_and_newcomer_boost(self):
        intro_post = {
            "platform": "skool.com",
            "community": "ai-automation-vault",
            "url": "https://www.skool.com/ai-automation-vault/welcome#c1",
            "author": "Marcus Vance",
            "author_handle": "@marcusv",
            "content_text": "Hey everyone! Just joined the group. Looking to learn how to build autonomous agents.",
            "is_introduction": True,
            "likes": 0,
            "replies": 0
        }

        score, rec = calculate_relevance_and_virality(intro_post, self.config)
        self.assertGreaterEqual(score, 75)
        self.assertEqual(rec, "viable")

    def test_newcomer_welcome_response_generation(self):
        intro_post = {
            "platform": "skool.com",
            "community": "ai-automation-vault",
            "url": "https://www.skool.com/ai-automation-vault/welcome#c1",
            "author": "Marcus Vance",
            "author_handle": "@marcusv",
            "content_text": "Hey everyone! Just joined the community. Excited to build our first multi-agent workforce.",
            "is_introduction": True
        }

        response = generate_op_response(intro_post, self.persona, "community_growth")
        self.assertIn("Welcome to the community", response)
        self.assertIn("@marcusv", response)
        self.assertIn("primary workflow", response)

    def test_developer_aws_advice_response_generation(self):
        tech_post = {
            "platform": "skool.com",
            "community": "ai-automation-vault",
            "url": "https://www.skool.com/ai-automation-vault/p-102",
            "author": "David Chen",
            "author_handle": "@dchen",
            "title": "AWS Lambda timeout error with Amplify backend",
            "content_text": "Getting a 504 gateway timeout when calling our custom Lambda from Amplify Gen 2.",
            "is_tech_bottleneck": True
        }

        response = generate_op_response(tech_post, self.persona, "support")
        self.assertIn("Great technical question", response)
        self.assertIn("@dchen", response)
        self.assertIn("Core Diagnostic", response)
        self.assertIn("Boundary Validation", response)

    def test_end_to_end_evaluation_and_dashboard_generation(self):
        raw_stream = """
Alice Smith @alicesmith
Hey all! Just joined the group. Excited to learn about autonomous coding pipelines!

Bob Developer @bob_dev
Anyone experiencing AWS Lambda timeouts with Amplify Gen 2 deployments when uploading large build artifacts?

Charlie Agent @charlie
Exploring how to persist agentic memory across sub-sessions without token bloat. Thoughts?
"""
        posts = parse_raw_text_stream(raw_stream, default_platform="skool.com", community="ai-automation-vault")
        self.assertEqual(len(posts), 3)

        # Process each post
        for p in posts:
            res = process_post_item(p, self.social_dir, self.db_path, self.config)
            self.assertEqual(res["status"], "drafted")

        # Export JSON
        export_res = export_to_json(self.test_dir)
        self.assertEqual(export_res["total_indexed"], 3)
        self.assertEqual(export_res["queue_count"], 3)

        # Generate Dashboard
        dash_file = generate_dashboard(self.test_dir)
        self.assertTrue(os.path.exists(dash_file))

        with open(dash_file, "r", encoding="utf-8") as f:
            dash_html = f.read()

        self.assertIn("Alice Smith", dash_html)
        self.assertIn("Bob Developer", dash_html)
        self.assertIn("Charlie Agent", dash_html)
        self.assertIn("Welcome to the community", dash_html)


if __name__ == "__main__":
    unittest.main()
