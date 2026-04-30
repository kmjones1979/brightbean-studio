"""Seed Partner=1Claw, Products=Shroud/Intents/Vault, and one GTMPlan per product.

Idempotent: safe to re-run. Only fills empty fields — never overwrites manual edits.

Usage:
    python manage.py seed_oneclaw_gtm --workspace-id <UUID>
    python manage.py seed_oneclaw_gtm --workspace-id <UUID> --demo-content
"""

from __future__ import annotations

import uuid
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.gtm.models import GTMPlan, GTMPlanStatus, Partner, Product
from apps.workspaces.models import Workspace

PROOF_URLS = [
    "https://1claw.xyz/shroud",
    "https://1claw.xyz/intents",
    "https://1claw.xyz/security",
    "https://docs.1claw.xyz",
    "https://docs.1claw.xyz/docs/intro",
    "https://docs.1claw.xyz/docs/quickstart",
    "https://docs.1claw.xyz/docs/agent-api/overview",
    "https://docs.1claw.xyz/docs/mcp/overview",
    "https://docs.1claw.xyz/docs/sdks/overview",
    "https://docs.1claw.xyz/docs/guides/shroud",
    "https://docs.1claw.xyz/docs/guides/intents-api",
    "https://docs.1claw.xyz/docs/guides/treasury",
    "https://docs.1claw.xyz/docs/guides/customer-managed-keys",
    "https://docs.1claw.xyz/docs/security",
]


SHROUD_PLAN = {
    "name": "Shroud — TEE LLM Proxy for Agent Security Teams",
    "audiences": [
        {
            "persona": "Security engineers at AI-first startups",
            "role_titles": ["Security Engineer", "Sec Eng", "AppSec Engineer"],
            "company_size": "20-500",
            "industries": ["AI/ML", "Developer tools", "SaaS"],
            "watering_holes": [
                "Hacker News",
                "r/netsec",
                "Lobste.rs",
                "Latent Space",
                "AI Engineer Foundation Discord",
            ],
        },
        {
            "persona": "Platform/SRE teams running production agents",
            "role_titles": ["Platform Engineer", "SRE", "Infra Lead"],
            "company_size": "50-1000",
            "industries": ["AI/ML", "Fintech", "Health-tech"],
            "watering_holes": [
                "Kubernetes Slack",
                "DevOps subreddits",
                "Last9 / Datadog blogs",
            ],
        },
        {
            "persona": "Compliance leads at fintech/health-tech",
            "role_titles": ["CISO", "Head of Compliance", "Security Architect"],
            "company_size": "200+",
            "industries": ["Fintech", "Health-tech", "Regulated SaaS"],
            "watering_holes": ["LinkedIn", "ISACA forums", "RSA Conference"],
        },
    ],
    "value_props": [
        "Vault-aware redaction: Aho-Corasick exact match, not regex",
        "Six-layer inspection pipeline: unicode normalization, command injection, social engineering, encoding obfuscation, network threat, filesystem",
        "Per-agent JSONB policy — centralized, no agent-side trust required",
        "Runs inside AMD SEV-SNP TEEs on GKE Confidential Nodes",
        "Drop-in: change base URL, keep your existing OpenAI/Anthropic SDK",
        "Redacted before the LLM saw anything — the provider never sees your secrets",
    ],
    "proof_points": [
        {
            "claim": "Shroud runs in AMD SEV-SNP TEEs on GKE Confidential Nodes",
            "evidence_url": "https://1claw.xyz/shroud",
            "evidence_type": "product_page",
        },
        {
            "claim": "Vault-aware redaction uses exact-match (Aho-Corasick) on the actual stored secret values",
            "evidence_url": "https://docs.1claw.xyz/docs/guides/shroud",
            "evidence_type": "docs",
        },
        {
            "claim": "Six-layer inspection pipeline catches injection, exfil, PII, encoding tricks",
            "evidence_url": "https://1claw.xyz/shroud",
            "evidence_type": "product_page",
        },
    ],
    "voice": {
        "tone": "Technical, direct, opinionated",
        "formality_1_to_5": 3,
        "humor_allowed": True,
        "emoji_policy": "Sparingly — only in informal X/Twitter posts, never in LinkedIn",
        "we_vs_i": "we",
        "reading_level": "Senior engineer / CISO",
    },
    "do_say": [
        "vault-aware",
        "inside the TEE",
        "per-agent policy",
        "Aho-Corasick exact match",
        "AMD SEV-SNP",
        "GKE Confidential Nodes",
        "redacted before the LLM saw anything",
        "centralized policy enforcement — no agent-side trust required",
    ],
    "do_not_say": [
        "SOC 2 certified",
        "HIPAA compliant",
        "ISO 27001 certified",
        "AI firewall",
    ],
    "competitors": [
        {"name": "LangSmith", "positioning_against": "Observability-only; no vault, no TEE"},
        {"name": "Generic LLM proxies", "positioning_against": "Regex-only redaction misses the actual secrets"},
        {"name": "HashiCorp Vault", "positioning_against": "No MCP, no LLM proxy, no agent-native auth"},
    ],
    "keywords_seo": [
        "AI agent security",
        "LLM proxy",
        "TEE confidential compute",
        "secrets manager for AI agents",
        "prompt injection mitigation",
        "AMD SEV-SNP",
    ],
    "cta_library": [
        {
            "label": "Read the Shroud docs",
            "url": "https://docs.1claw.xyz/docs/guides/shroud",
            "intent": "docs",
        },
        {
            "label": "Talk to us",
            "url": "https://calendly.com/buidl/intro-call",
            "intent": "demo",
        },
        {
            "label": "Start free — 1,000 requests / month",
            "url": "https://1claw.xyz/login",
            "intent": "signup",
        },
    ],
    "compliance_notes": (
        "SOC 2 Type I in progress (do NOT claim 'SOC 2 certified'); SOC 2 Type II target TBD; "
        "GDPR controls present; BAA/HIPAA/ISO 27001 are case-by-case — never claim outright."
    ),
}


INTENTS_PLAN = {
    "name": "Intents — TEE Transaction Signing for DeFi Agents",
    "audiences": [
        {
            "persona": "DeFi product engineers",
            "role_titles": ["Smart Contract Engineer", "Protocol Engineer", "Full-Stack DeFi"],
            "company_size": "5-100",
            "industries": ["DeFi", "DAO tooling", "On-chain automation"],
            "watering_holes": ["Crypto X/Twitter", "Farcaster", "Mirror", "Discord guilds"],
        },
        {
            "persona": "Treasury ops at crypto-native companies",
            "role_titles": ["Head of Treasury", "Finance Lead", "Operations"],
            "company_size": "10-200",
            "industries": ["Crypto-native SaaS", "DAOs", "Web3 infra"],
            "watering_holes": ["LinkedIn", "Twitter", "Bankless newsletter"],
        },
        {
            "persona": "x402 / agentic payments builders",
            "role_titles": ["Founder", "Protocol Engineer"],
            "company_size": "Solo - 20",
            "industries": ["AI agents", "x402 payments"],
            "watering_holes": ["x402 Discord", "Coinbase CDP forums", "Base ecosystem"],
        },
    ],
    "value_props": [
        "Keys never leave hardware — agents submit intents, the TEE signs",
        "Per-agent allowlists, value caps, daily caps",
        "Tenderly simulation pre-broadcast — no surprise reverts",
        "109+ EVM chains: Ethereum, Base, Arbitrum, Optimism, Polygon, etc.",
        "x402 micropayments via Coinbase CDP facilitator on Base — agents pay for their own API calls in USDC",
        "EIP-1559 + legacy signing, replay protection, idempotency keys",
    ],
    "proof_points": [
        {
            "claim": "109+ EVM chains supported, including Ethereum, Base, Arbitrum, Optimism, Polygon",
            "evidence_url": "https://1claw.xyz/intents",
            "evidence_type": "product_page",
        },
        {
            "claim": "Transaction simulation via Tenderly before broadcast",
            "evidence_url": "https://docs.1claw.xyz/docs/guides/intents-api",
            "evidence_type": "docs",
        },
        {
            "claim": "x402 micropayments via Coinbase CDP on Base",
            "evidence_url": "https://1claw.xyz/intents",
            "evidence_type": "product_page",
        },
    ],
    "voice": {
        "tone": "Crypto-native, direct, builder-to-builder",
        "formality_1_to_5": 2,
        "humor_allowed": True,
        "emoji_policy": "Yes on X (especially 🤖, 🔐, ⛓️), sparingly on LinkedIn",
        "we_vs_i": "we",
        "reading_level": "Senior DeFi engineer",
    },
    "do_say": [
        "intent, not signature",
        "key never left the TEE",
        "Tenderly-simulated",
        "per-agent allowlist",
        "EIP-1559 + legacy",
        "x402 on Base via Coinbase CDP",
    ],
    "do_not_say": [
        "non-custodial wallet",
        "investment advice",
        "guaranteed",
        "audited smart contracts",
    ],
    "competitors": [
        {"name": "MPC wallet SDKs", "positioning_against": "Agent-unaware; no per-agent policy or allowlist"},
        {"name": "Hot wallets", "positioning_against": "Key in agent runtime = key in LLM context = leak"},
    ],
    "keywords_seo": [
        "AI agent transactions",
        "TEE transaction signing",
        "x402 payments",
        "agentic DeFi",
        "EVM agent wallet",
        "Coinbase CDP",
    ],
    "cta_library": [
        {
            "label": "Read the Intents API docs",
            "url": "https://docs.1claw.xyz/docs/guides/intents-api",
            "intent": "docs",
        },
        {
            "label": "Schedule a demo",
            "url": "https://calendly.com/buidl/intro-call",
            "intent": "demo",
        },
        {
            "label": "View pricing",
            "url": "https://1claw.xyz/pricing",
            "intent": "signup",
        },
    ],
    "compliance_notes": (
        "Intents API is on Business and Enterprise plans only — NEVER imply free-tier availability. "
        "Custodial-in-TEE: do not claim 'non-custodial'. No investment advice, no guarantees."
    ),
}


VAULT_PLAN = {
    "name": "Vault & Security — Cloud HSM for Humans and AI Agents",
    "audiences": [
        {
            "persona": "CTOs and security leads at agent companies",
            "role_titles": ["CTO", "VP Eng", "Head of Security"],
            "company_size": "10-500",
            "industries": ["AI/ML", "SaaS", "Developer tools"],
            "watering_holes": ["LinkedIn", "X", "Founder communities"],
        },
        {
            "persona": "Platform engineers replacing Doppler/Infisical/HashiCorp Vault",
            "role_titles": ["Platform Engineer", "DevOps", "SRE"],
            "company_size": "50-2000",
            "industries": ["SaaS", "AI/ML", "Fintech"],
            "watering_holes": ["DevOps Slack groups", "r/devops", "HashiCorp forums"],
        },
        {
            "persona": "Compliance teams preparing SOC 2",
            "role_titles": ["Compliance Lead", "Security Architect", "GRC"],
            "company_size": "100+",
            "industries": ["Regulated SaaS", "Fintech", "Health-tech"],
            "watering_holes": ["Drata/Vanta blogs", "ISACA"],
        },
    ],
    "value_props": [
        "Three-layer envelope encryption: Cloud KMS root → per-vault KEK → per-secret DEK",
        "FIPS 140-2 Level 3 HSM root of trust",
        "Optional CMEK (Customer-Managed Encryption Keys)",
        "MPC modes: 2-of-2 client custody (XOR), 2-of-3 multi-HSM Shamir across GCP/AWS/Azure, or combined",
        "Tamper-evident hash-chained audit log",
        "90-day audit export for compliance teams",
    ],
    "proof_points": [
        {
            "claim": "Three-layer envelope encryption with HSM-backed root keys",
            "evidence_url": "https://1claw.xyz/security",
            "evidence_type": "product_page",
        },
        {
            "claim": "Multi-cloud MPC: Shamir 2-of-3 across GCP, AWS, Azure",
            "evidence_url": "https://docs.1claw.xyz/docs/security",
            "evidence_type": "docs",
        },
        {
            "claim": "Tamper-evident hash-chained audit log with 90-day export",
            "evidence_url": "https://1claw.xyz/security",
            "evidence_type": "product_page",
        },
    ],
    "voice": {
        "tone": "Authoritative, infrastructure-veteran, plain-spoken",
        "formality_1_to_5": 4,
        "humor_allowed": False,
        "emoji_policy": "None on LinkedIn, minimal on X",
        "we_vs_i": "we",
        "reading_level": "CTO / CISO / Senior platform engineer",
    },
    "do_say": [
        "envelope encryption",
        "HSM root of trust",
        "MPC",
        "Shamir 2-of-3",
        "tamper-evident hash chain",
        "scoped, audited, revocable",
    ],
    "do_not_say": [
        "SOC 2 certified",
        "HIPAA compliant",
        "ISO 27001 certified",
    ],
    "competitors": [
        {
            "name": "HashiCorp Vault",
            "positioning_against": "Heavy ops burden, no MCP, not agent-native",
        },
        {"name": "Doppler", "positioning_against": "No HSM, no MPC, no MCP"},
        {"name": "Infisical", "positioning_against": "No HSM, no MPC"},
        {"name": "AWS Secrets Manager", "positioning_against": "Single-cloud, not agent-native"},
    ],
    "keywords_seo": [
        "secrets management",
        "Cloud HSM",
        "envelope encryption",
        "multi-cloud secrets",
        "MPC key splitting",
        "Doppler alternative",
    ],
    "cta_library": [
        {
            "label": "Read the security architecture docs",
            "url": "https://docs.1claw.xyz/docs/security",
            "intent": "docs",
        },
        {
            "label": "Schedule a security review",
            "url": "https://calendly.com/buidl/intro-call",
            "intent": "demo",
        },
        {
            "label": "Sign up free",
            "url": "https://1claw.xyz/login",
            "intent": "signup",
        },
    ],
    "compliance_notes": (
        "SOC 2 Type I in progress; never claim 'SOC 2 certified' or any other certification "
        "that 1Claw has not actually achieved. State only what's documented on /security."
    ),
}


PRODUCT_DEFS = [
    (
        "Shroud",
        {
            "tagline": "TEE-protected LLM proxy with vault-aware redaction",
            "category": "AI Security",
            "homepage_url": "https://1claw.xyz/shroud",
            "docs_url": "https://docs.1claw.xyz/docs/guides/shroud",
            "pricing_url": "https://1claw.xyz/pricing",
        },
        SHROUD_PLAN,
    ),
    (
        "Intents",
        {
            "tagline": "TEE transaction signing for on-chain AI agents",
            "category": "Web3",
            "homepage_url": "https://1claw.xyz/intents",
            "docs_url": "https://docs.1claw.xyz/docs/guides/intents-api",
            "pricing_url": "https://1claw.xyz/pricing",
        },
        INTENTS_PLAN,
    ),
    (
        "Vault",
        {
            "tagline": "HSM-backed envelope encryption with multi-cloud MPC",
            "category": "Secrets Management",
            "homepage_url": "https://1claw.xyz/security",
            "docs_url": "https://docs.1claw.xyz/docs/security",
            "pricing_url": "https://1claw.xyz/pricing",
        },
        VAULT_PLAN,
    ),
]


class Command(BaseCommand):
    help = "Seed Partner=1Claw, Products=Shroud/Intents/Vault, and one GTMPlan per product."

    def add_arguments(self, parser):
        parser.add_argument(
            "--workspace-id",
            type=str,
            required=False,
            help="UUID of the workspace to seed into. If omitted, uses the first workspace.",
        )
        parser.add_argument(
            "--demo-content",
            action="store_true",
            help="Also generate stub AIGeneration rows (Phase 2 — currently a no-op).",
        )

    def handle(self, *args, **options):
        workspace = self._resolve_workspace(options.get("workspace_id"))
        partner = self._upsert_partner(workspace)

        plans_for_demo = []
        for product_name, product_fields, plan_data in PRODUCT_DEFS:
            product = self._upsert_product(partner, product_name, product_fields)
            plan = self._upsert_plan(workspace, partner, product, plan_data)
            plans_for_demo.append(plan)

        if options.get("demo_content"):
            self._seed_demo_generations(workspace, plans_for_demo)

        self.stdout.write(self.style.SUCCESS(f"Seeded 1Claw GTM data into workspace {workspace.name}"))

    def _seed_demo_generations(self, workspace, plans):
        """Populate ~10 stubbed AIGeneration rows per plan using the StubProvider.
        No real LLM calls. Useful for screenshots and review without API keys.
        """
        try:
            from apps.ai.models import (
                AIGeneration,
                GenerationKind,
                GenerationStatus,
            )
        except ImportError:
            self.stdout.write(self.style.WARNING("  --demo-content skipped: apps.ai not installed."))
            return

        kinds = [
            GenerationKind.CAPTION,
            GenerationKind.MULTI_PLATFORM,
            GenerationKind.HOOK,
            GenerationKind.CTA,
            GenerationKind.HASHTAGS,
        ]
        platforms = ["twitter", "linkedin_personal", "bluesky"]
        sample_briefs = [
            "Announce that our MCP server now ships 17 native tools",
            "Why 'agents need credentials too' is the AI security story of 2026",
            "Quick demo: redacting a Stripe key before it hits the LLM",
            "Comparison post — vault-aware redaction vs regex-only",
            "Behind the scenes: AMD SEV-SNP TEE on GKE",
        ]

        created = 0
        for plan in plans:
            for i in range(10):
                kind = kinds[i % len(kinds)]
                platform = platforms[i % len(platforms)]
                brief = sample_briefs[i % len(sample_briefs)]
                AIGeneration.objects.create(
                    workspace=workspace,
                    actor=None,
                    kind=kind,
                    gtm_plan=plan,
                    input_payload={"brief": brief, "platform": platform, "demo": True},
                    provider="stub",
                    model="claude-sonnet-4-6",
                    routed_via_shroud=False,
                    output_payload={
                        "text": f"[demo] {brief} — variant {i + 1}",
                    },
                    prompt_tokens=150,
                    completion_tokens=80,
                    cost_usd_micro=1_650,
                    latency_ms=420,
                    status=GenerationStatus.SUCCEEDED,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"  + Seeded {created} stubbed AIGenerations"))

    def _resolve_workspace(self, workspace_id_arg) -> Workspace:
        if workspace_id_arg:
            try:
                return Workspace.objects.get(id=uuid.UUID(workspace_id_arg))
            except (Workspace.DoesNotExist, ValueError) as exc:
                raise CommandError(f"Workspace {workspace_id_arg} not found") from exc

        ws = Workspace.objects.order_by("created_at").first()
        if not ws:
            raise CommandError("No workspaces exist. Create one first or pass --workspace-id.")
        return ws

    def _upsert_partner(self, workspace: Workspace) -> Partner:
        partner, created = Partner.objects.get_or_create(
            workspace=workspace,
            slug="1claw",
            defaults={
                "name": "1Claw",
                "website": "https://1claw.xyz",
                "notes": "HSM-backed secret management for humans and AI agents.",
            },
        )
        if not created:
            self.stdout.write("  Partner '1Claw' already exists — leaving as-is.")
        else:
            self.stdout.write(self.style.SUCCESS("  + Created Partner '1Claw'"))
        return partner

    def _upsert_product(self, partner: Partner, name: str, fields: dict[str, Any]) -> Product:
        slug_value = name.lower()
        product, created = Product.objects.get_or_create(
            partner=partner,
            slug=slug_value,
            defaults={"name": name, **fields},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  + Created Product '{name}'"))
        else:
            self._fill_missing(product, fields)
            self.stdout.write(f"  Product '{name}' already exists — filled missing fields.")
        return product

    def _upsert_plan(
        self,
        workspace: Workspace,
        partner: Partner,
        product: Product,
        plan_data: dict[str, Any],
    ) -> GTMPlan:
        slug_value = f"{product.slug}-plan"
        plan, created = GTMPlan.objects.get_or_create(
            workspace=workspace,
            slug=slug_value,
            defaults={
                "partner": partner,
                "product": product,
                "status": GTMPlanStatus.ACTIVE,
                **plan_data,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  + Created Plan '{plan.name}'"))
        else:
            self._fill_missing(plan, plan_data)
            self.stdout.write(f"  Plan '{plan.name}' already exists — filled missing fields.")
        return plan

    def _fill_missing(self, instance, fields: dict[str, Any]) -> None:
        """Only fill fields that are currently empty/falsy. Never overwrite."""
        changed = False
        for key, value in fields.items():
            current = getattr(instance, key, None)
            if not current:
                setattr(instance, key, value)
                changed = True
        if changed:
            instance.save()
