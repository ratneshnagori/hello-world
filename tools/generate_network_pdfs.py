#!/usr/bin/env python3
"""Generate interview-prep PDFs for core AWS networking topics.

Each topic gets its own styled PDF (cover, TOC, 13 sections, glossary) plus a
bespoke architecture diagram. Run:  python3 tools/generate_network_pdfs.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_lib import (  # noqa: E402
    PDF, build_pdf, NAVY, BLUE, GREY, GREEN, RED, ORANGE, PURPLE, TEAL,
    PUBLIC_FILL, PRIVATE_FILL, ISOLATED_FILL,
)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")

LEFT = 20
WIDTH = 170

FAIL_HDR = ["Failure", "Symptom", "Typical root cause"]
FAIL_W = [40, 50, 84]
COST_HDR = ["Cost driver", "Why it adds up", "Mitigation"]
COST_W = [38, 76, 60]
GLOS_HDR = ["Term", "Meaning"]
GLOS_W = [42, 132]


# --------------------------------------------------------------------------- #
# Diagram helpers
# --------------------------------------------------------------------------- #
def internet_box(pdf, x, y, w=34, h=8, label="Internet"):
    pdf.diag_box(x, y, w, h, BLUE, BLUE, title=None)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(x, y + 1.5)
    pdf.cell(w, 4, label, align="C")
    pdf.set_text_color(0, 0, 0)


def diagram_intro(pdf, h2, body):
    pdf.add_page()
    pdf.h2(h2)
    pdf.body(body)


# --------------------------------------------------------------------------- #
# 1. SUBNETS
# --------------------------------------------------------------------------- #
def diagram_subnets(pdf):
    diagram_intro(
        pdf, "Reference Diagram - Carving a VPC into subnets",
        "A single VPC CIDR (10.0.0.0/16, ~65k addresses) is divided into smaller "
        "per-AZ subnets. Each subnet lives in exactly one Availability Zone and is "
        "tagged public, private, or isolated by how its route table is configured.")
    top = pdf.get_y() + 4
    pdf.diag_box(LEFT, top, WIDTH, 96, (245, 248, 252), NAVY,
                 title="VPC  10.0.0.0/16   (65,536 addresses)", title_size=9)
    az_w = 78
    az_h = 80
    az_top = top + 9
    layout = [
        ("Public  10.0.0.0/24", "251 usable - route 0/0 -> IGW", PUBLIC_FILL, GREEN),
        ("Private 10.0.10.0/24", "251 usable - route 0/0 -> NAT", PRIVATE_FILL, BLUE),
        ("Isolated 10.0.20.0/24", "251 usable - no 0/0 route", ISOLATED_FILL, RED),
    ]
    for i, az in enumerate(["Availability Zone A", "Availability Zone B"]):
        ax = LEFT + 6 + i * (az_w + 6)
        pdf.diag_box(ax, az_top, az_w, az_h, (255, 255, 255), BLUE,
                     title=az, title_color=BLUE)
        sy = az_top + 7
        for label, note, fill, edge in layout:
            lab = label.replace("0.0/24", f"{i}.0/24") if i == 1 else label
            pdf.diag_box(ax + 2.5, sy, az_w - 5, 20, fill, edge,
                         title=lab, lines=[note])
            sy += 23.5
    pdf.diag_caption(
        LEFT, top + 98, WIDTH,
        "AWS reserves 5 addresses per subnet (network, VPC router, DNS, future use, "
        "broadcast). Subnet size is fixed at creation - plan CIDRs up front. "
        "'Public vs private' is not a flag; it is determined by the route table.")
    pdf.ln(2)


SUBNETS = {
    "title": "Subnets",
    "subtitle": "Segmenting a VPC into Addressable, AZ-Scoped Networks",
    "blurb": "Problem & motivation - CIDR math & reserved IPs - public/private/isolated - "
             "routing & packet flow - failure modes - scaling - security - "
             "observability & automation - cost - troubleshooting - real-world patterns",
    "summary": (
        "A subnet is a contiguous slice of a VPC's IP address space that is bound to a "
        "single Availability Zone. Subnets are the unit at which you attach a route table "
        "and a network ACL, and they are where elastic network interfaces (and therefore "
        "instances, containers, load balancers, and databases) actually live. Whether a "
        "subnet is 'public', 'private', or 'isolated' is decided entirely by its route "
        "table and the gateways it can reach - not by any single attribute. This guide "
        "covers CIDR planning, the AZ relationship, packet flow, failure modes, scaling, "
        "security, observability, automation, cost, and troubleshooting."),
    "sections": [
        ("The Problem It Solves", [
            ("body", "A flat /16 network with thousands of hosts is hard to secure, hard to "
             "reason about, and ties everything to one failure domain. Subnets let you "
             "segment that space so different tiers get different reachability, blast "
             "radius is contained, and resources can be spread across AZs."),
            ("h2", "Core needs subnets address"),
            ("kv", [
                ("Segmentation", "Separate web/app/data tiers with distinct routing and "
                 "filtering so the database is never directly internet-reachable."),
                ("AZ placement", "A subnet maps to exactly one AZ; spreading subnets across "
                 "AZs is how you build highly available, multi-AZ architectures."),
                ("Blast-radius control", "Per-subnet route tables and NACLs limit how far a "
                 "misconfiguration or compromise can spread."),
                ("Address organization", "Predictable CIDR allocation makes routing, "
                 "peering, and on-prem integration tractable."),
            ]),
        ]),
        ("How It Works Internally", [
            ("body", "A subnet is defined by a CIDR block that is a subset of the VPC CIDR "
             "and must not overlap any sibling subnet. AWS reserves 5 addresses in every "
             "subnet: the network address, the implied VPC router (.1), the DNS resolver "
             "(.2), a reserved address (.3), and the broadcast address. So a /24 yields 251 "
             "usable IPs, not 256."),
            ("bullets", [
                "Each subnet is associated with exactly one route table (the VPC 'main' "
                "table by default) and one network ACL.",
                "Instances launched into a subnet receive an ENI with a private IP from the "
                "subnet's range; the ENI is the real network identity.",
                "The subnet's AZ is fixed at creation and cannot be changed - to move AZs "
                "you create a new subnet.",
                "IPv6 subnets are always /64; IPv4 subnet sizing is your choice within the "
                "VPC block.",
            ]),
            ("diagram", diagram_subnets),
        ]),
        ("Traffic Flow, Packet Flow & Routing Decisions", [
            ("h2", "How a subnet decides where a packet goes"),
            ("bullets", [
                "An instance in subnet 10.0.10.0/24 sends a packet; the source ENI's "
                "security group (egress) is evaluated first (stateful).",
                "The subnet's route table is consulted using longest-prefix match: the VPC "
                "local route covers in-VPC traffic; 0.0.0.0/0 sends the rest to IGW/NAT/etc.",
                "The subnet's NACL is applied at the subnet boundary (stateless) on the way "
                "out and back in.",
                "Return traffic is allowed automatically by the security group; the NACL "
                "must explicitly allow ephemeral ports.",
            ]),
            ("callout", ("Public vs private - the real definition",
             "A subnet is 'public' only if its route table has a 0.0.0.0/0 route to an "
             "Internet Gateway AND the instance has a public/elastic IP. Remove that route "
             "and the same subnet becomes private. There is no 'isPublic' switch.", GREEN)),
        ]),
        ("Advantages & Disadvantages", [
            ("h2", "Advantages"),
            ("bullets", [
                "Fine-grained segmentation and per-tier reachability.",
                "Natural mapping to AZs for high availability.",
                "Smaller blast radius via per-subnet route tables and NACLs.",
                "Clear, auditable structure for security and compliance.",
            ]),
            ("h2", "Disadvantages / costs"),
            ("bullets", [
                "CIDR sizing is permanent - undersizing forces painful re-architecture.",
                "More subnets means more route tables/NACLs to manage and keep consistent.",
                "Each AZ needs its own subnet, multiplying objects in large designs.",
                "IP exhaustion within a subnet silently blocks new launches.",
            ]),
        ]),
        ("Common Failure Modes", [
            ("table", (FAIL_HDR, [
                ["IP exhaustion", "Launches fail / no free IP", "Subnet CIDR too small for "
                 "ENIs (esp. EKS/Fargate density)."],
                ["Wrong route table", "Unexpected public/no egress", "Subnet associated with "
                 "main table instead of intended custom table."],
                ["Single-AZ design", "Outage when one AZ fails", "Critical subnet not "
                 "replicated across AZs."],
                ["CIDR overlap", "Cannot create / peer", "New subnet overlaps a sibling or "
                 "peered VPC range."],
                ["NACL blocks returns", "One-way connectivity", "Stateless NACL missing "
                 "ephemeral-port allow."],
                ["Reserved-IP confusion", "Off-by-5 capacity errors", "Forgetting AWS "
                 "reserves 5 IPs per subnet."],
            ], FAIL_W)),
        ]),
        ("Scaling Considerations", [
            ("kv", [
                ("Right-size CIDRs", "Plan for peak ENI count (pods, tasks, instances), not "
                 "current usage; prefer larger subnets for container platforms."),
                ("AZ fan-out", "Create symmetric subnets in 2-3 AZs per tier for HA."),
                ("Secondary CIDRs", "Attach additional CIDR blocks to a VPC when the "
                 "original space runs out."),
                ("IPAM", "Use centralized IP Address Management to avoid overlaps across many "
                 "accounts/regions."),
                ("Prefix delegation", "On EKS, prefix delegation packs more pods per node "
                 "without exhausting subnet IPs."),
            ]),
        ]),
        ("Security Implications", [
            ("bullets", [
                "Put only internet-facing resources (ALB, NAT) in public subnets.",
                "Keep app tiers in private subnets and data tiers in isolated subnets with no "
                "egress route.",
                "Attach restrictive NACLs as a coarse, subnet-wide backstop to security "
                "groups.",
                "Never rely on subnet placement alone - combine with security groups and "
                "app-layer auth (zero trust).",
            ]),
        ]),
        ("Observability, Reliability & Automation", [
            ("h2", "Observability"),
            ("bullets", [
                "Enable VPC Flow Logs per subnet to see accepted/rejected flows.",
                "Track free-IP / ENI counts to catch exhaustion before it bites.",
            ]),
            ("h2", "Reliability"),
            ("bullets", [
                "Replicate every tier's subnet across multiple AZs.",
                "Ensure NAT/egress exists per-AZ so an AZ loss does not break others.",
            ]),
            ("h2", "Automation"),
            ("bullets", [
                "Define subnets in IaC (Terraform/CloudFormation/CDK) with computed CIDRs.",
                "Use IPAM + policy checks to prevent overlaps and enforce naming/tags.",
            ]),
        ]),
        ("Cost Considerations", [
            ("table", (COST_HDR, [
                ["Cross-AZ traffic", "Per-GB charge between subnets in different AZs.",
                 "Co-locate chatty components; AZ-aware routing."],
                ["NAT per AZ", "One NAT GW per AZ multiplies hourly + data cost.",
                 "Balance HA vs cost; consolidate where risk allows."],
                ["Wasted address space", "Oversized subnets reserve IPs unused.",
                 "Right-size; reclaim with secondary CIDRs as needed."],
            ], COST_W)),
        ]),
        ("Troubleshooting Approach", [
            ("body", "Walk the subnet's configuration in order:"),
            ("bullets", [
                "1. Which subnet/AZ is the ENI in, and is there a free IP?",
                "2. Which route table is associated, and what is the 0.0.0.0/0 target?",
                "3. Do the NACL rules allow both directions (incl. ephemeral ports)?",
                "4. Do security groups on the ENI allow the flow?",
                "5. Read Flow Logs and run Reachability Analyzer for proof.",
            ]),
            ("callout", ("Mnemonic", "'AZ -> Route table -> NACL -> SG -> Flow logs.' Most "
             "subnet connectivity issues are a wrong route-table association or an "
             "ephemeral-port NACL gap.", GREEN)),
        ]),
        ("Real-World Examples & Patterns", [
            ("kv", [
                ("3-tier per AZ", "public (ALB/NAT) + private (app) + isolated (DB) subnets "
                 "replicated across 2-3 AZs."),
                ("EKS large subnets", "Use /20 or larger private subnets to accommodate "
                 "per-pod ENIs and prefix delegation."),
                ("Shared egress", "Small public subnets hosting only NAT; large private "
                 "subnets for workloads."),
                ("Landing zone", "IPAM-managed, non-overlapping subnet CIDRs standardized "
                 "across many accounts."),
            ]),
        ]),
        ("Senior-Level Trade-offs & Talking Points", [
            ("bullets", [
                "Few large subnets vs many small subnets: simpler IP management vs finer "
                "isolation and blast-radius control.",
                "Subnet-per-tier-per-AZ object explosion vs operational simplicity.",
                "Reserve generous CIDRs now (cheap) vs re-architecting later (expensive).",
                "NACL backstop vs complexity: stateless rules add safety but are easy to "
                "misorder.",
            ]),
            ("callout", ("Whiteboard checklist",
             "(1) Draw VPC CIDR. (2) Slice per-AZ public/private/isolated subnets. (3) Show "
             "route-table association per subnet. (4) Mark reserved IPs and usable count. "
             "(5) Trace a packet out and back. (6) Discuss AZ HA, IP exhaustion, and "
             "cross-AZ cost.")),
        ]),
        ("Quick Glossary", [
            ("table", (GLOS_HDR, [
                ["CIDR", "IP range notation (e.g., /24 = 256 addresses, 251 usable)."],
                ["AZ", "Availability Zone; a subnet belongs to exactly one."],
                ["ENI", "Elastic Network Interface - the real network identity of a resource."],
                ["Public subnet", "Subnet whose route table sends 0/0 to an Internet Gateway."],
                ["Isolated subnet", "Subnet with no default route off the VPC."],
                ["Secondary CIDR", "Extra address block added to a VPC when space runs out."],
                ["IPAM", "IP Address Management for planning/allocating non-overlapping CIDRs."],
            ], GLOS_W)),
        ]),
    ],
}


# --------------------------------------------------------------------------- #
# 2. ROUTE TABLES
# --------------------------------------------------------------------------- #
def diagram_route_tables(pdf):
    diagram_intro(
        pdf, "Reference Diagram - How a route table steers traffic",
        "A route table is an ordered set of (destination CIDR -> target) rules. Each "
        "subnet is associated with one route table; the router applies longest-prefix "
        "match to pick the next hop. Below: a custom 'public' table and the rules a "
        "private subnet would use instead.")
    top = pdf.get_y() + 4
    # public route table
    rt_w = 82
    pdf.diag_box(LEFT, top, rt_w, 52, (255, 255, 255), GREEN,
                 title="Public subnet route table", title_color=GREEN)
    rows = [("10.0.0.0/16", "local"), ("0.0.0.0/0", "igw-0a1b"),
            ("172.16.0.0/16", "pcx-peer"), ("S3 prefix list", "vpce-gw")]
    ry = top + 7
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(LEFT + 2, ry); pdf.cell(40, 4, "Destination")
    pdf.set_xy(LEFT + 44, ry); pdf.cell(36, 4, "Target")
    ry += 5
    for dst, tgt in rows:
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(30, 30, 30)
        pdf.set_xy(LEFT + 2, ry); pdf.cell(40, 4, dst)
        pdf.set_xy(LEFT + 44, ry); pdf.cell(36, 4, tgt)
        ry += 5.2
    # private route table
    px = LEFT + rt_w + 6
    pdf.diag_box(px, top, rt_w, 52, (255, 255, 255), BLUE,
                 title="Private subnet route table", title_color=BLUE)
    rows2 = [("10.0.0.0/16", "local"), ("0.0.0.0/0", "nat-09c"),
             ("S3 prefix list", "vpce-gw"), ("(no IGW route)", "-")]
    ry = top + 7
    pdf.set_font("Helvetica", "B", 7.5); pdf.set_text_color(*NAVY)
    pdf.set_xy(px + 2, ry); pdf.cell(40, 4, "Destination")
    pdf.set_xy(px + 44, ry); pdf.cell(36, 4, "Target")
    ry += 5
    for dst, tgt in rows2:
        pdf.set_font("Helvetica", "", 7.5); pdf.set_text_color(30, 30, 30)
        pdf.set_xy(px + 2, ry); pdf.cell(40, 4, dst)
        pdf.set_xy(px + 44, ry); pdf.cell(36, 4, tgt)
        ry += 5.2
    # subnets pointing up
    sy = top + 64
    pdf.diag_box(LEFT + 10, sy, 60, 12, PUBLIC_FILL, GREEN,
                 title="Public subnet", lines=["assoc -> public table"])
    pdf.diag_box(px + 10, sy, 60, 12, PRIVATE_FILL, BLUE,
                 title="Private subnet", lines=["assoc -> private table"])
    pdf.diag_arrow(LEFT + 40, sy, LEFT + 40, top + 52, color=GREEN)
    pdf.diag_arrow(px + 40, sy, px + 40, top + 52, color=BLUE)
    pdf.diag_caption(
        LEFT, sy + 16, WIDTH,
        "Longest-prefix match wins: 10.0.5.7 matches local (/16) over 0.0.0.0/0. The "
        "local route is implicit and cannot be removed. A subnet not explicitly "
        "associated falls back to the VPC 'main' route table.")
    pdf.ln(2)


ROUTE_TABLES = {
    "title": "Route Tables",
    "subtitle": "The Forwarding Logic That Steers Every VPC Packet",
    "blurb": "Problem & motivation - longest-prefix match - targets & propagation - "
             "packet flow - failure modes - scaling - security - observability & "
             "automation - cost - troubleshooting - real-world patterns",
    "summary": (
        "A route table is the control surface that decides the next hop for every packet "
        "leaving a subnet. It is an ordered list of routes, each mapping a destination CIDR "
        "(or managed prefix list) to a target such as the local VPC, an Internet Gateway, a "
        "NAT Gateway, a peering connection, a Transit Gateway, or a gateway endpoint. The "
        "router uses longest-prefix match to choose the most specific route. Route tables "
        "are where 'public vs private' is actually decided, and where most VPC connectivity "
        "bugs are found. This guide covers internals, packet flow, failure modes, scaling, "
        "security, observability, automation, cost, and troubleshooting."),
    "sections": [
        ("The Problem It Solves", [
            ("body", "Resources need a deterministic, auditable way to decide where traffic "
             "goes: stay inside the VPC, exit to the internet, reach a peer or on-prem "
             "network, or hit a managed service privately. Route tables provide that "
             "decision layer per subnet, decoupled from the instances themselves."),
            ("h2", "Core needs route tables address"),
            ("kv", [
                ("Next-hop decisions", "Map destinations to gateways/targets without "
                 "touching instance OS routing."),
                ("Segmentation", "Different subnets get different egress (public vs private "
                 "vs isolated) by associating different tables."),
                ("Connectivity composition", "Combine IGW, NAT, peering, TGW, VGW, and "
                 "endpoints into one coherent forwarding policy."),
                ("Auditability", "Routing becomes declarative configuration, reviewable and "
                 "versioned."),
            ]),
        ]),
        ("How It Works Internally", [
            ("body", "Every VPC has an implicit, highly available router. Route tables are "
             "the rules that router consults. Each table contains an un-removable local "
             "route for the VPC CIDR (and each secondary CIDR) plus the routes you add. "
             "Routes can be static (you set them) or propagated (learned dynamically from a "
             "VGW/Transit Gateway via BGP)."),
            ("bullets", [
                "Selection uses longest-prefix match; for equal prefixes, static routes are "
                "preferred over propagated ones.",
                "Targets include: local, igw, nat, eni, pcx (peering), tgw, vgw, gateway "
                "endpoints, and egress-only IGW (IPv6).",
                "Managed prefix lists let you reference a named set of CIDRs (e.g., S3) in a "
                "route or rule.",
                "A subnet uses its explicitly associated table, else the VPC main table.",
            ]),
            ("diagram", diagram_route_tables),
        ]),
        ("Traffic Flow, Packet Flow & Routing Decisions", [
            ("h2", "Decision order for an outbound packet"),
            ("bullets", [
                "Packet leaves ENI; security group egress evaluated (stateful).",
                "Router scans the subnet's route table for the most specific matching "
                "destination (longest-prefix match).",
                "Local route always wins for in-VPC destinations and cannot be overridden.",
                "Static vs propagated tie-break: static preferred; among propagated, BGP "
                "attributes decide.",
                "Chosen target forwards the packet (IGW, NAT, TGW, peering, endpoint, ...).",
            ]),
            ("callout", ("Common gotcha - asymmetric routing",
             "If the outbound subnet routes via NAT but the return-path subnet/table routes "
             "differently (or a peering route is missing on one side), you get one-way "
             "connectivity. Routes must be consistent in BOTH directions.", ORANGE)),
        ]),
        ("Advantages & Disadvantages", [
            ("h2", "Advantages"),
            ("bullets", [
                "Declarative, per-subnet control of all forwarding.",
                "Composes many connectivity types into one policy.",
                "Dynamic propagation (BGP) reduces manual route sprawl with VGW/TGW.",
                "Easy to reason about with longest-prefix match.",
            ]),
            ("h2", "Disadvantages / costs"),
            ("bullets", [
                "Route-entry limits cap how many explicit routes a table can hold.",
                "Easy to misconfigure (wrong target, missing return route, overlaps).",
                "No native ordering/priority beyond prefix length and static/propagated.",
                "Propagated + static interactions can surprise operators.",
            ]),
        ]),
        ("Common Failure Modes", [
            ("table", (FAIL_HDR, [
                ["Missing 0/0 route", "No internet egress", "Forgot IGW/NAT default route on "
                 "the subnet's table."],
                ["Wrong association", "Subnet unexpectedly public/private", "Subnet bound to "
                 "main table instead of intended one."],
                ["Asymmetric routes", "One-way / intermittent", "Return path lacks a matching "
                 "route (peering/TGW/NAT)."],
                ["Blackhole route", "Silent drops", "Target deleted; route now points to "
                 "nothing (blackhole)."],
                ["Overlapping prefixes", "Wrong next hop chosen", "A more specific route "
                 "steers traffic unexpectedly."],
                ["Entry-limit hit", "Cannot add route", "Too many explicit CIDRs; needs "
                 "summarization."],
            ], FAIL_W)),
        ]),
        ("Scaling Considerations", [
            ("kv", [
                ("Summarize", "Aggregate CIDRs (supernet) to stay under route-entry limits."),
                ("Prefer dynamic", "Use BGP propagation with VGW/TGW so routes scale without "
                 "manual entries."),
                ("Prefix lists", "Reference managed prefix lists to keep rules compact and "
                 "centrally updatable."),
                ("Hub routing", "At many-VPC scale, centralize with Transit Gateway route "
                 "tables instead of N^2 peering routes."),
                ("Separation", "Use distinct tables per tier to keep each small and clear."),
            ]),
        ]),
        ("Security Implications", [
            ("bullets", [
                "Routing IS a security control: removing a 0/0->IGW route makes a subnet "
                "private.",
                "Avoid overly broad routes that expose isolated/data subnets.",
                "Use isolated tables (only local + endpoints) for sensitive data tiers.",
                "Alert on route changes - they can silently open or sever connectivity.",
                "Centralized inspection: route egress through a firewall/appliance subnet.",
            ]),
        ]),
        ("Observability, Reliability & Automation", [
            ("h2", "Observability"),
            ("bullets", [
                "Reachability Analyzer to prove a path exists (or find the broken hop).",
                "Flow Logs to see whether traffic reaches the expected next hop.",
                "Detect blackhole routes (deleted targets) via config monitoring.",
            ]),
            ("h2", "Reliability"),
            ("bullets", [
                "The VPC router itself is HA and managed; design redundant targets per AZ.",
                "Ensure failover paths exist (e.g., per-AZ NAT) so one target loss is "
                "contained.",
            ]),
            ("h2", "Automation"),
            ("bullets", [
                "Define routes in IaC; avoid console drift.",
                "Policy-as-code to forbid 0/0->IGW on data-tier tables.",
            ]),
        ]),
        ("Cost Considerations", [
            ("table", (COST_HDR, [
                ["Route tables themselves", "Free - no charge for tables or routes.",
                 "N/A; the cost is in the targets they point to."],
                ["NAT/TGW targets", "Routes to NAT/TGW drive data-processing cost.",
                 "Use gateway endpoints (free for S3/DynamoDB) where possible."],
                ["Suboptimal paths", "Routing cross-AZ/cross-region adds transfer cost.",
                 "Design routes to keep traffic local when feasible."],
            ], COST_W)),
        ]),
        ("Troubleshooting Approach", [
            ("body", "When traffic does not flow, suspect routing first:"),
            ("bullets", [
                "1. Which table is the source subnet associated with?",
                "2. Is there a matching route to the destination, and what is the target?",
                "3. Is the target healthy (not a blackhole / deleted)?",
                "4. Does the RETURN subnet/table have a matching route back?",
                "5. Confirm with Reachability Analyzer + Flow Logs.",
            ]),
            ("callout", ("Mnemonic", "'Association -> Match -> Target -> Return.' Verify both "
             "directions; asymmetric routing is the classic silent failure.", GREEN)),
        ]),
        ("Real-World Examples & Patterns", [
            ("kv", [
                ("Public/private split", "Separate tables: public->IGW, private->NAT, both "
                 "with gateway endpoints."),
                ("Inspection VPC", "Routes steer all egress through a firewall appliance "
                 "subnet before the internet."),
                ("Hub-and-spoke", "TGW route tables segment which VPCs can reach which, "
                 "centrally."),
                ("Hybrid", "VGW route propagation injects on-prem prefixes learned via BGP."),
            ]),
        ]),
        ("Senior-Level Trade-offs & Talking Points", [
            ("bullets", [
                "Static vs propagated routes: predictability vs scalability/auto-failover.",
                "Many specific routes vs summarized routes: precision vs entry limits.",
                "Per-subnet tables vs shared tables: isolation vs management overhead.",
                "Distributed routing (peering) vs centralized (TGW route tables): latency/cost "
                "vs operability.",
            ]),
            ("callout", ("Whiteboard checklist",
             "(1) Draw subnets and their associated tables. (2) List destination->target "
             "rules. (3) Show longest-prefix match picking a hop. (4) Trace return path. "
             "(5) Discuss propagation, blackholes, limits, and inspection routing.")),
        ]),
        ("Quick Glossary", [
            ("table", (GLOS_HDR, [
                ["Local route", "Implicit, un-removable route for the VPC CIDR(s)."],
                ["Longest-prefix match", "Most specific matching CIDR wins."],
                ["Target", "Next hop: igw, nat, pcx, tgw, vgw, eni, endpoint, etc."],
                ["Propagated route", "Route learned dynamically via BGP from VGW/TGW."],
                ["Main route table", "Default table used by subnets with no explicit assoc."],
                ["Blackhole", "Route whose target no longer exists; traffic is dropped."],
                ["Prefix list", "Named, reusable set of CIDRs for routes/rules."],
            ], GLOS_W)),
        ]),
    ],
}


# --------------------------------------------------------------------------- #
# 3. INTERNET GATEWAY
# --------------------------------------------------------------------------- #
def diagram_igw(pdf):
    diagram_intro(
        pdf, "Reference Diagram - Internet Gateway data path",
        "An Internet Gateway (IGW) is a horizontally scaled, redundant, VPC-attached "
        "component that performs 1:1 NAT between an instance's public IP and its private "
        "IP, enabling bidirectional internet connectivity for resources in public "
        "subnets.")
    top = pdf.get_y() + 6
    internet_box(pdf, LEFT + 68, top, 38, 9, "Internet")
    # VPC box
    vy = top + 22
    pdf.diag_box(LEFT, vy, WIDTH, 62, (245, 248, 252), NAVY,
                 title="VPC  10.0.0.0/16", title_size=9)
    # IGW on edge
    igw_w = 40
    pdf.diag_box(LEFT + 65, vy - 6, igw_w, 12, BLUE, BLUE,
                 title=None)
    pdf.diag_label(LEFT + 65, vy - 4, "Internet Gateway", color=(255, 255, 255),
                   bold=True, w=igw_w, align="C", size=8)
    # public subnet
    pdf.diag_box(LEFT + 12, vy + 14, 146, 40, (255, 255, 255), GREEN,
                 title="Public subnet 10.0.0.0/24  (route 0.0.0.0/0 -> igw)",
                 title_color=GREEN)
    pdf.diag_box(LEFT + 22, vy + 26, 60, 20, PUBLIC_FILL, GREEN,
                 title="EC2 / ALB", lines=["private 10.0.0.10", "public 52.x.x.x (EIP)"])
    pdf.diag_box(LEFT + 96, vy + 26, 50, 20, PUBLIC_FILL, GREEN,
                 title="Route table", lines=["local -> VPC", "0/0 -> igw-0a1b"])
    # arrows
    pdf.diag_arrow(LEFT + 87, top + 9, LEFT + 85, vy - 6, color=GREY)
    pdf.diag_arrow(LEFT + 85, vy - 6 + 12, LEFT + 52, vy + 36, color=GREEN)
    pdf.diag_caption(
        LEFT, vy + 58, WIDTH,
        "Flow: instance (private 10.0.0.10 + EIP) -> route table 0/0 -> IGW -> IGW rewrites "
        "source to the public IP -> Internet. Inbound reverses. The IGW is free, "
        "auto-scaled, and never a single point of failure. No public IP = no internet, even "
        "with an IGW route.")
    pdf.ln(2)


INTERNET_GATEWAY = {
    "title": "Internet Gateway",
    "subtitle": "Bidirectional, Highly Available Internet Connectivity for a VPC",
    "blurb": "Problem & motivation - 1:1 NAT internals - public IP requirement - packet "
             "flow - failure modes - scaling - security - observability & automation - "
             "cost - troubleshooting - real-world patterns",
    "summary": (
        "An Internet Gateway (IGW) is the VPC component that enables resources with public "
        "IP addresses to communicate with the internet in both directions. It is a managed, "
        "horizontally scaled, redundant target - not an instance - so it imposes no "
        "bandwidth bottleneck and no availability risk. The IGW performs one-to-one network "
        "address translation between an instance's public/elastic IP and its private IP. "
        "Crucially, an IGW alone is not enough: a subnet needs a 0.0.0.0/0 route to the IGW "
        "AND the instance needs a public IP. This guide covers internals, packet flow, "
        "failure modes, scaling, security, observability, automation, cost, and "
        "troubleshooting."),
    "sections": [
        ("The Problem It Solves", [
            ("body", "Instances in a VPC use private RFC 1918 addresses that are not "
             "routable on the public internet. Something must bridge that private space to "
             "the internet, scale to any traffic level, and stay highly available. The IGW "
             "is that bridge for inbound and outbound public traffic."),
            ("h2", "Core needs the IGW addresses"),
            ("kv", [
                ("Public reachability", "Let internet clients reach public-facing services "
                 "(web servers, load balancers)."),
                ("Outbound for public hosts", "Let instances with public IPs initiate "
                 "internet connections."),
                ("Address translation", "Map private IPs <-> public/elastic IPs without "
                 "per-instance NAT software."),
                ("No bottleneck", "Provide internet connectivity without a throughput or "
                 "availability single point of failure."),
            ]),
        ]),
        ("How It Works Internally", [
            ("body", "An IGW is attached to a VPC (one IGW per VPC). It is implemented in "
             "the AWS network fabric as a horizontally scaled, redundant service rather than "
             "an EC2 instance, so it has no managed bandwidth limit and no maintenance "
             "windows. For traffic to use it, the source subnet's route table must point "
             "0.0.0.0/0 (or specific public CIDRs) at the IGW."),
            ("bullets", [
                "It performs 1:1 NAT: outbound, it rewrites the instance's private source IP "
                "to its associated public/elastic IP; inbound, it does the reverse.",
                "If an instance has only a private IP (no public/EIP), the IGW cannot give it "
                "internet access - it has nothing to translate to.",
                "IGW is stateless from the customer's perspective; security is enforced by "
                "security groups and NACLs.",
                "For IPv6, an egress-only Internet Gateway provides outbound-only access.",
            ]),
            ("diagram", diagram_igw),
        ]),
        ("Traffic Flow, Packet Flow & Routing Decisions", [
            ("h2", "Outbound packet via IGW"),
            ("bullets", [
                "Instance (private 10.0.0.10, public 52.x.x.x) sends to an internet host.",
                "Security group egress is evaluated (stateful).",
                "Route table: 0.0.0.0/0 -> igw target.",
                "IGW rewrites the source IP from private to the instance's public IP.",
                "Packet exits to the internet; replies return to the public IP and the IGW "
                "maps them back to the private IP.",
            ]),
            ("callout", ("The #1 IGW gotcha",
             "An IGW route is necessary but NOT sufficient. The instance must also have a "
             "public IPv4 or Elastic IP. A private-only instance in a 'public' subnet still "
             "cannot reach the internet through an IGW - it needs NAT instead.", ORANGE)),
        ]),
        ("Advantages & Disadvantages", [
            ("h2", "Advantages"),
            ("bullets", [
                "Fully managed, horizontally scaled, and redundant - no SPOF.",
                "No hourly charge for the gateway itself.",
                "Supports both inbound and outbound public traffic.",
                "No bandwidth ceiling to manage.",
            ]),
            ("h2", "Disadvantages / costs"),
            ("bullets", [
                "Exposes resources publicly if misused - requires disciplined SG/NACL/routing.",
                "Only useful for resources that have public IPs.",
                "One IGW per VPC; cannot segment internet egress within a VPC by IGW.",
                "Standard internet data-transfer-out charges still apply.",
            ]),
        ]),
        ("Common Failure Modes", [
            ("table", (FAIL_HDR, [
                ["IGW not attached", "No internet at all", "IGW created but not attached to "
                 "the VPC."],
                ["No 0/0 route", "Timeouts", "Subnet route table missing default route to "
                 "IGW."],
                ["No public IP", "Outbound fails", "Instance has only a private IP; needs "
                 "EIP or NAT."],
                ["SG/NACL block", "Refused/one-way", "Security group or NACL denies the "
                 "port/return traffic."],
                ["Public IP not assigned", "Intermittent after restart", "Auto-assign public "
                 "IP off; ephemeral IP lost on stop/start."],
            ], FAIL_W)),
        ]),
        ("Scaling Considerations", [
            ("kv", [
                ("Throughput", "IGW scales automatically; no action needed for bandwidth."),
                ("HA", "IGW is inherently redundant - nothing to make multi-AZ."),
                ("Egress design", "For many private hosts, pair public subnets (IGW) with NAT "
                 "for private subnets."),
                ("EIP limits", "Public IPv4 / EIP quotas can bound how many public hosts you "
                 "run; request increases as needed."),
            ]),
        ]),
        ("Security Implications", [
            ("bullets", [
                "An IGW route turns a subnet public - apply it deliberately and narrowly.",
                "Lock down inbound with security groups (default deny) and NACLs.",
                "Prefer load balancers in public subnets and keep app/data tiers private.",
                "Use VPC Flow Logs and GuardDuty to watch for exposure and abuse.",
                "Consider AWS Network Firewall / WAF in front of internet-facing services.",
            ]),
        ]),
        ("Observability, Reliability & Automation", [
            ("h2", "Observability"),
            ("bullets", [
                "Flow Logs to see internet-bound accepts/rejects.",
                "CloudWatch/metrics on the public-facing resources (ALB/EC2), not the IGW "
                "itself (the IGW exposes no per-gateway metrics).",
            ]),
            ("h2", "Reliability"),
            ("bullets", [
                "IGW is managed and redundant; reliability work focuses on your resources.",
                "Spread public-facing resources (ALB targets) across AZs.",
            ]),
            ("h2", "Automation"),
            ("bullets", [
                "Create + attach IGW and add routes in IaC.",
                "Guardrails to flag new 0/0->IGW routes on sensitive subnets.",
            ]),
        ]),
        ("Cost Considerations", [
            ("table", (COST_HDR, [
                ["IGW gateway", "No hourly/processing charge for the IGW.",
                 "N/A - the IGW is free."],
                ["Data transfer out", "Internet egress (GB out) is billed.",
                 "CDN/caching, compression, fewer external calls."],
                ["Public IPv4", "Public/Elastic IPv4 addresses now carry an hourly charge.",
                 "Release unused EIPs; consolidate behind load balancers; use IPv6."],
            ], COST_W)),
        ]),
        ("Troubleshooting Approach", [
            ("body", "For 'instance can't reach the internet':"),
            ("bullets", [
                "1. Is an IGW attached to the VPC?",
                "2. Does the subnet's route table have 0.0.0.0/0 -> igw?",
                "3. Does the instance have a public/Elastic IP?",
                "4. Do SG (egress) and NACL (both directions) allow the traffic?",
                "5. Confirm with Reachability Analyzer + Flow Logs.",
            ]),
            ("callout", ("Mnemonic", "'Attached -> Route -> Public IP -> SG/NACL.' If the "
             "host has no public IP, an IGW will never help - use a NAT Gateway.", GREEN)),
        ]),
        ("Real-World Examples & Patterns", [
            ("kv", [
                ("Public ALB", "Internet-facing load balancer in public subnets fronting "
                 "private app servers."),
                ("Bastion (legacy)", "A jump host with an EIP in a public subnet (prefer SSM "
                 "Session Manager instead)."),
                ("Egress-only IPv6", "Outbound-only internet for IPv6 private workloads via "
                 "egress-only IGW."),
                ("Public + NAT combo", "Public subnets host IGW-facing LB/NAT; private "
                 "subnets reach internet via NAT."),
            ]),
        ]),
        ("Senior-Level Trade-offs & Talking Points", [
            ("bullets", [
                "Public IP per instance vs load balancer + private fleet: simplicity vs "
                "security and IPv4 cost.",
                "IGW (bidirectional) vs NAT (outbound-only) vs egress-only IGW (IPv6): pick "
                "by direction and IP family.",
                "Single IGW per VPC: simple but no per-IGW egress segmentation - use routing "
                "and inspection instead.",
                "IPv4 cost pressure vs IPv6 adoption readiness.",
            ]),
            ("callout", ("Whiteboard checklist",
             "(1) Draw VPC + attached IGW. (2) Public subnet with 0/0->IGW. (3) Instance with "
             "public IP. (4) Show 1:1 NAT out and back. (5) Contrast with NAT GW for private "
             "hosts. (6) Discuss SG/NACL, IPv4 cost, and exposure risk.")),
        ]),
        ("Quick Glossary", [
            ("table", (GLOS_HDR, [
                ["IGW", "Internet Gateway - bidirectional internet access for public IPs."],
                ["Egress-only IGW", "Outbound-only internet access for IPv6."],
                ["EIP", "Elastic IP - a static public IPv4 address you own."],
                ["1:1 NAT", "Mapping one private IP to one public IP (what the IGW does)."],
                ["Public subnet", "Subnet with a 0/0 route to an IGW."],
                ["Auto-assign public IP", "Subnet setting granting ephemeral public IPv4."],
                ["DTO", "Data Transfer Out - billed internet egress."],
            ], GLOS_W)),
        ]),
    ],
}


# --------------------------------------------------------------------------- #
# 4. NAT GATEWAY
# --------------------------------------------------------------------------- #
def diagram_nat(pdf):
    diagram_intro(
        pdf, "Reference Diagram - NAT Gateway data path",
        "A NAT Gateway lets instances in private subnets initiate OUTBOUND internet "
        "connections (updates, API calls) while blocking unsolicited INBOUND connections. "
        "It performs source NAT using its Elastic IP and lives in a public subnet.")
    top = pdf.get_y() + 6
    internet_box(pdf, LEFT + 68, top, 38, 9, "Internet")
    vy = top + 22
    pdf.diag_box(LEFT, vy, WIDTH, 70, (245, 248, 252), NAVY,
                 title="VPC  10.0.0.0/16", title_size=9)
    pdf.diag_box(LEFT + 60, vy - 6, 50, 12, BLUE, BLUE)
    pdf.diag_label(LEFT + 60, vy - 4, "Internet Gateway", color=(255, 255, 255),
                   bold=True, w=50, align="C", size=8)
    # public subnet with NAT
    pdf.diag_box(LEFT + 8, vy + 12, 154, 24, (255, 255, 255), GREEN,
                 title="Public subnet (route 0/0 -> IGW)", title_color=GREEN)
    pdf.diag_box(LEFT + 100, vy + 20, 54, 12, PUBLIC_FILL, GREEN,
                 title="NAT Gateway", lines=["EIP 52.x.x.x"])
    # private subnet
    pdf.diag_box(LEFT + 8, vy + 40, 154, 24, (255, 255, 255), BLUE,
                 title="Private subnet (route 0/0 -> NAT)", title_color=BLUE)
    pdf.diag_box(LEFT + 14, vy + 48, 60, 12, PRIVATE_FILL, BLUE,
                 title="App instance", lines=["private 10.0.10.5"])
    # arrows
    pdf.diag_arrow(LEFT + 74, vy + 54, LEFT + 127, vy + 32, color=BLUE)
    pdf.diag_arrow(LEFT + 127, vy + 20, LEFT + 85, vy - 6 + 12, color=GREEN)
    pdf.diag_arrow(LEFT + 85, top + 9, LEFT + 85, vy - 6, color=GREY)
    pdf.diag_caption(
        LEFT, vy + 66, WIDTH,
        "Flow: private app (10.0.10.5) -> 0/0 NAT -> NAT rewrites source to its EIP -> "
        "public subnet 0/0 IGW -> Internet. Replies return to the EIP and NAT maps them "
        "back. Inbound-initiated connections are dropped. Deploy one NAT per AZ for HA.")
    pdf.ln(2)


NAT_GATEWAY = {
    "title": "NAT Gateway",
    "subtitle": "Outbound-Only Internet Access for Private Subnets",
    "blurb": "Problem & motivation - source NAT internals - port allocation - packet flow - "
             "failure modes - scaling - security - observability & automation - cost - "
             "troubleshooting - real-world patterns",
    "summary": (
        "A NAT (Network Address Translation) Gateway lets instances in private subnets make "
        "outbound connections to the internet - for OS updates, package installs, and "
        "third-party API calls - while preventing the internet from initiating connections "
        "back to them. It is a managed, AZ-scoped service that performs source NAT using an "
        "Elastic IP and sits in a public subnet. NAT Gateways are a frequent source of cost "
        "surprises and AZ-failure blind spots, making them a favorite senior-interview "
        "topic. This guide covers internals, packet flow, failure modes, scaling, security, "
        "observability, automation, cost, and troubleshooting."),
    "sections": [
        ("The Problem It Solves", [
            ("body", "Private instances must stay unreachable from the internet for "
             "security, yet still need to pull updates and call external services. A NAT "
             "Gateway squares that circle: outbound allowed, inbound (unsolicited) blocked."),
            ("h2", "Core needs the NAT Gateway addresses"),
            ("kv", [
                ("Safe egress", "Outbound internet for private hosts without giving them "
                 "public IPs."),
                ("Inbound protection", "Drop unsolicited inbound connections by design "
                 "(stateful translation)."),
                ("Managed scale", "Handle high connection volume without managing NAT "
                 "instances."),
                ("Stable source IP", "Present a consistent Elastic IP to external services "
                 "for allow-listing."),
            ]),
        ]),
        ("How It Works Internally", [
            ("body", "A NAT Gateway is deployed into a specific public subnet (and thus a "
             "specific AZ) and is given an Elastic IP. Private subnets route 0.0.0.0/0 to the "
             "NAT Gateway. It maintains a stateful translation table: it rewrites the private "
             "source IP/port to its own EIP and a chosen source port, tracks the flow, and "
             "reverses the translation for return packets."),
            ("bullets", [
                "It supports a large number of simultaneous connections and scales bandwidth "
                "automatically up to tens of Gbps.",
                "Source-port space per unique destination is finite (~64k per destination "
                "IP:port), so very high fan-out to ONE endpoint can cause port exhaustion.",
                "It is AZ-scoped: a NAT Gateway only survives as long as its AZ; you need one "
                "per AZ for HA.",
                "It is stateful, so only the responses to outbound flows are allowed back "
                "in.",
            ]),
            ("diagram", diagram_nat),
        ]),
        ("Traffic Flow, Packet Flow & Routing Decisions", [
            ("h2", "Outbound via NAT"),
            ("bullets", [
                "Private instance (10.0.10.5) -> external API; SG egress evaluated.",
                "Private subnet route table: 0.0.0.0/0 -> nat-gw target.",
                "NAT GW rewrites source to its EIP + a source port; records the flow.",
                "Public subnet route table: 0.0.0.0/0 -> IGW; packet exits.",
                "Replies arrive at the EIP; NAT maps them back to 10.0.10.5; SG allows the "
                "return statefully.",
            ]),
            ("callout", ("AZ-affinity gotcha",
             "Route each AZ's private subnet to the NAT Gateway IN THAT SAME AZ. If AZ-b "
             "private subnets route to a NAT in AZ-a, you pay cross-AZ data charges AND lose "
             "egress for AZ-b if AZ-a fails.", ORANGE)),
        ]),
        ("Advantages & Disadvantages", [
            ("h2", "Advantages"),
            ("bullets", [
                "Fully managed, auto-scaling, no NAT instances to patch.",
                "Stateful inbound protection by default.",
                "Stable EIP for external allow-listing.",
                "High throughput and connection capacity.",
            ]),
            ("h2", "Disadvantages / costs"),
            ("bullets", [
                "Charged per hour AND per GB processed - a top cost-surprise.",
                "AZ-scoped: needs one per AZ for true HA (more cost).",
                "Port exhaustion possible with massive fan-out to a single endpoint.",
                "Outbound-only - cannot accept inbound-initiated connections.",
            ]),
        ]),
        ("Common Failure Modes", [
            ("table", (FAIL_HDR, [
                ["Single-AZ NAT", "AZ failure kills egress", "Only one NAT GW; other AZs "
                 "route to it."],
                ["Wrong route", "No outbound", "Private subnet 0/0 not pointing at NAT (or "
                 "points at IGW with no public IP)."],
                ["Port exhaustion", "Intermittent connect errors", "Huge fan-out to one "
                 "dest IP:port exhausts source ports."],
                ["NAT in private subnet", "NAT itself can't egress", "NAT GW placed in a "
                 "subnet without 0/0 -> IGW."],
                ["Bandwidth/conn limits", "Throttling at extreme scale", "Exceeding per-GW "
                 "limits; need multiple GWs."],
                ["Cost blowout", "Surprise bill", "All egress (incl. S3) routed through NAT "
                 "instead of endpoints."],
            ], FAIL_W)),
        ]),
        ("Scaling Considerations", [
            ("kv", [
                ("One NAT per AZ", "Deploy a NAT Gateway in each AZ and route locally for HA "
                 "and to avoid cross-AZ charges."),
                ("Endpoints to offload", "Use gateway/interface endpoints so S3/DynamoDB and "
                 "AWS APIs bypass NAT entirely."),
                ("Spread destinations", "Port exhaustion is per dest IP:port - many "
                 "destinations scale fine; single-endpoint fan-out does not."),
                ("Multiple NATs", "For extreme egress, distribute across several NAT GWs."),
            ]),
        ]),
        ("Security Implications", [
            ("bullets", [
                "NAT prevents inbound-initiated connections - good default for private hosts.",
                "It does NOT filter outbound destinations; add egress filtering (Network "
                "Firewall / proxy) if needed.",
                "Its EIP can be allow-listed by partners; protect that IP's stability.",
                "Monitor for data-exfiltration patterns in egress traffic.",
            ]),
        ]),
        ("Observability, Reliability & Automation", [
            ("h2", "Observability"),
            ("bullets", [
                "CloudWatch metrics: BytesOutToDestination, ActiveConnectionCount, "
                "ErrorPortAllocation (port exhaustion signal), PacketsDropCount.",
                "Flow Logs to attribute egress to source instances.",
            ]),
            ("h2", "Reliability"),
            ("bullets", [
                "Per-AZ NAT Gateways with per-AZ routing remove the cross-AZ SPOF.",
                "Alarm on ErrorPortAllocation and packet drops.",
            ]),
            ("h2", "Automation"),
            ("bullets", [
                "Provision one NAT per AZ via IaC, wiring per-AZ route tables.",
                "Cost guardrails: detect S3/DynamoDB traffic flowing through NAT.",
            ]),
        ]),
        ("Cost Considerations", [
            ("table", (COST_HDR, [
                ["Hourly charge", "Each NAT GW bills per hour, per AZ.",
                 "Right-size AZ count; tear down dev/test NATs."],
                ["Data processing", "Per-GB processed on top of transfer-out.",
                 "Route S3/DynamoDB/AWS APIs via VPC endpoints (no NAT)."],
                ["Cross-AZ via NAT", "Routing to a NAT in another AZ adds transfer cost.",
                 "Per-AZ NAT + per-AZ routing."],
            ], COST_W)),
        ]),
        ("Troubleshooting Approach", [
            ("body", "For 'private instance can't reach the internet':"),
            ("bullets", [
                "1. Private subnet route table: 0.0.0.0/0 -> the correct (same-AZ) NAT GW?",
                "2. Is the NAT GW in a PUBLIC subnet whose table has 0/0 -> IGW?",
                "3. Does the NAT GW have an Elastic IP and 'available' status?",
                "4. SG egress + NACL (both directions, ephemeral ports) allow it?",
                "5. Check ErrorPortAllocation for exhaustion; read Flow Logs.",
            ]),
            ("callout", ("Mnemonic", "'NAT route -> NAT in public subnet -> EIP -> SG/NACL.' "
             "Remember the NAT itself needs an IGW path to actually egress.", GREEN)),
        ]),
        ("Real-World Examples & Patterns", [
            ("kv", [
                ("Per-AZ NAT", "One NAT GW per AZ; each private subnet routes to its local "
                 "NAT."),
                ("Endpoint offload", "Gateway endpoints for S3/DynamoDB + interface "
                 "endpoints for AWS APIs to cut NAT cost."),
                ("Centralized egress", "Route all spoke-VPC egress through NAT in a shared "
                 "egress VPC via Transit Gateway."),
                ("Allow-listed source", "Partner allow-lists the NAT's EIP for outbound API "
                 "calls."),
            ]),
        ]),
        ("Senior-Level Trade-offs & Talking Points", [
            ("bullets", [
                "NAT Gateway vs self-managed NAT instance: managed HA/scale vs cost control "
                "and custom features.",
                "Per-AZ NAT (HA, no cross-AZ fees) vs single NAT (cheaper, risky).",
                "Centralized egress VPC (governance, fewer NATs) vs per-VPC NAT (lower "
                "latency, blast-radius isolation).",
                "VPC endpoints reduce NAT cost but add their own per-endpoint charges - model "
                "the break-even.",
            ]),
            ("callout", ("Whiteboard checklist",
             "(1) Draw private subnet -> NAT (public subnet) -> IGW. (2) Show source NAT to "
             "EIP. (3) One NAT per AZ with local routing. (4) Add endpoints to offload S3. "
             "(5) Discuss cost (hourly + per-GB), port exhaustion, and AZ failure.")),
        ]),
        ("Quick Glossary", [
            ("table", (GLOS_HDR, [
                ["NAT", "Network Address Translation - rewrites source IP/port for egress."],
                ["Source NAT", "Translating the source address of outbound packets."],
                ["EIP", "Elastic IP attached to the NAT for a stable egress address."],
                ["Port exhaustion", "Running out of source ports to ONE destination."],
                ["AZ-scoped", "A NAT GW lives in one AZ; needs peers for HA."],
                ["Gateway endpoint", "Free private path to S3/DynamoDB, bypassing NAT."],
                ["ErrorPortAllocation", "CloudWatch metric signaling port exhaustion."],
            ], GLOS_W)),
        ]),
    ],
}


# --------------------------------------------------------------------------- #
# 5. SECURITY GROUPS
# --------------------------------------------------------------------------- #
def diagram_sg(pdf):
    diagram_intro(
        pdf, "Reference Diagram - Stateful security group around an ENI",
        "A security group is a stateful, allow-only virtual firewall attached to elastic "
        "network interfaces. Because it is stateful, any flow you allow OUT is "
        "automatically allowed back IN (and vice versa) - you never write return rules.")
    top = pdf.get_y() + 4
    pdf.diag_box(LEFT, top, WIDTH, 84, (245, 248, 252), NAVY,
                 title="Subnet", title_size=9)
    # SG boundary
    pdf.diag_box(LEFT + 45, top + 10, 80, 64, (255, 255, 255), GREEN,
                 title="Security Group (stateful)", title_color=GREEN)
    pdf.diag_box(LEFT + 62, top + 44, 46, 22, PRIVATE_FILL, BLUE,
                 title="EC2 / ENI", lines=["10.0.10.5"])
    # inbound rules
    pdf.diag_box(LEFT + 50, top + 20, 70, 9, (224, 240, 226), GREEN,
                 title="Inbound: allow 443 from 0.0.0.0/0; 22 from 10.0.0.0/8",
                 title_size=7)
    # outbound rules
    pdf.diag_box(LEFT + 50, top + 31, 70, 9, (224, 240, 226), GREEN,
                 title="Outbound: allow all (default)", title_size=7)
    # arrows showing stateful return
    pdf.diag_arrow(LEFT + 10, top + 30, LEFT + 45, top + 30, color=BLUE)
    pdf.diag_label(LEFT + 6, top + 24, "request 443", color=BLUE, size=7, w=40)
    pdf.diag_arrow(LEFT + 45, top + 40, LEFT + 10, top + 40, color=GREEN)
    pdf.diag_label(LEFT + 6, top + 41, "reply (auto-allowed)", color=GREEN, size=7, w=42)
    pdf.diag_caption(
        LEFT, top + 86, WIDTH,
        "Rules are allow-only (no explicit deny). Default inbound = deny all; default "
        "outbound = allow all. Sources can be CIDRs or OTHER security groups (chaining), "
        "e.g., allow the app SG to reach the DB SG on 5432.")
    pdf.ln(2)


SECURITY_GROUPS = {
    "title": "Security Groups",
    "subtitle": "Stateful, Allow-Only Virtual Firewalls at the Instance Edge",
    "blurb": "Problem & motivation - statefulness - SG referencing/chaining - packet flow - "
             "failure modes - scaling - security - observability & automation - cost - "
             "troubleshooting - real-world patterns",
    "summary": (
        "A security group (SG) is a stateful, instance-level virtual firewall attached to "
        "elastic network interfaces. It contains allow-only rules; there is no explicit "
        "deny. Because it is stateful, response traffic for an allowed flow is permitted "
        "automatically, so you never write return rules. The standout feature is that rule "
        "sources/destinations can be OTHER security groups, enabling identity-based, "
        "self-updating microsegmentation. SGs are the primary, most-used network control in "
        "a VPC. This guide covers internals, packet flow, failure modes, scaling, security, "
        "observability, automation, cost, and troubleshooting."),
    "sections": [
        ("The Problem It Solves", [
            ("body", "Workloads need least-privilege network access that follows the "
             "resource, not the subnet, and that updates automatically as fleets scale up "
             "and down. Security groups provide per-ENI, identity-aware allow rules that are "
             "simple to reason about and stateful by default."),
            ("h2", "Core needs security groups address"),
            ("kv", [
                ("Least privilege", "Open only the exact ports/sources each resource needs."),
                ("Statefulness", "Permit return traffic automatically - no error-prone "
                 "ephemeral-port rules."),
                ("Identity-based rules", "Reference other SGs so rules track dynamic, "
                 "autoscaling fleets without IP churn."),
                ("Per-resource scope", "Controls travel with the ENI regardless of subnet."),
            ]),
        ]),
        ("How It Works Internally", [
            ("body", "A security group is evaluated in the data plane (in AWS Nitro/host "
             "hardware) for every packet to/from the ENIs it is attached to. It holds two "
             "rule sets - inbound and outbound - each a list of allow rules keyed by "
             "protocol, port range, and source/destination (CIDR, another SG, or a prefix "
             "list). There is no deny rule and no rule ordering; if any rule allows the "
             "packet it is permitted."),
            ("bullets", [
                "Stateful connection tracking: an allowed outbound flow's replies are "
                "auto-allowed inbound, and vice versa.",
                "Defaults: deny all inbound, allow all outbound (until you tighten it).",
                "Up to several SGs can attach to one ENI; their allow rules are unioned.",
                "Referencing another SG (e.g., 'allow from sg-app') auto-includes all current "
                "members of that SG - no IP lists to maintain.",
            ]),
            ("diagram", diagram_sg),
        ]),
        ("Traffic Flow, Packet Flow & Routing Decisions", [
            ("h2", "How SGs participate in a flow"),
            ("bullets", [
                "Inbound packet to an ENI: the union of that ENI's SG inbound rules is "
                "checked; if allowed, accepted.",
                "Because SGs are stateful, the response leaves without needing an explicit "
                "outbound rule.",
                "Outbound-initiated flows: outbound rules checked; responses auto-allowed "
                "inbound.",
                "SGs do not affect routing - routing is the route table's job; SGs only "
                "permit/deny.",
            ]),
            ("callout", ("Stateful vs stateless",
             "Unlike NACLs (stateless), SGs track connection state, so you only define the "
             "direction that INITIATES a connection. This eliminates the classic "
             "ephemeral-port mistake.", GREEN)),
        ]),
        ("Advantages & Disadvantages", [
            ("h2", "Advantages"),
            ("bullets", [
                "Stateful - simple, fewer mistakes.",
                "Identity-based via SG referencing - scales with dynamic fleets.",
                "Per-ENI granularity that follows the workload.",
                "Enforced in hardware at line rate.",
            ]),
            ("h2", "Disadvantages / costs"),
            ("bullets", [
                "Allow-only: cannot express an explicit deny/blocklist (use NACLs/firewall).",
                "Rule and SG-per-ENI quotas can constrain very complex policies.",
                "Over-broad rules (0.0.0.0/0 on sensitive ports) are a common risk.",
                "No central ordering/priority - reasoning about large rule sets gets hard.",
            ]),
        ]),
        ("Common Failure Modes", [
            ("table", (FAIL_HDR, [
                ["Missing inbound allow", "Connection refused/timeout", "Required port/source "
                 "not permitted inbound."],
                ["Tightened egress", "Outbound app calls fail", "Default allow-all egress "
                 "replaced without needed allows."],
                ["Wrong SG attached", "Unexpected exposure/block", "ENI has the wrong SG set."],
                ["Over-broad rule", "Security exposure", "0.0.0.0/0 on 22/3389/db ports."],
                ["SG-reference confusion", "Cross-SG flow blocked", "Rule references the "
                 "wrong SG, or peering needs CIDR not SG-ref."],
                ["Quota exceeded", "Cannot add rule/SG", "Hit rules-per-SG or SGs-per-ENI "
                 "limits."],
            ], FAIL_W)),
        ]),
        ("Scaling Considerations", [
            ("kv", [
                ("Reference, don't enumerate", "Use SG-to-SG rules instead of long IP lists "
                 "so policy scales with autoscaling."),
                ("Prefix lists", "Group common CIDRs into managed prefix lists referenced by "
                 "many SGs."),
                ("Tiered SGs", "One SG per role (web/app/db) and chain them rather than "
                 "per-instance SGs."),
                ("Quotas", "Watch rules-per-SG and SGs-per-ENI; request increases for "
                 "complex environments."),
                ("Cross-VPC caveat", "SG referencing works within a VPC/peered-and-enabled "
                 "contexts; across boundaries you may need CIDRs."),
            ]),
        ]),
        ("Security Implications", [
            ("bullets", [
                "Default deny inbound; open the minimum necessary.",
                "Prefer SG references over wide CIDRs for east-west traffic.",
                "Never expose management ports (22/3389) to 0.0.0.0/0 - use SSM/bastion.",
                "Tighten egress for sensitive tiers to curb exfiltration and lateral movement.",
                "Treat SGs as code; review every change.",
            ]),
        ]),
        ("Observability, Reliability & Automation", [
            ("h2", "Observability"),
            ("bullets", [
                "Flow Logs show REJECT entries when an SG/NACL blocks a flow.",
                "Reachability Analyzer pinpoints which SG rule is missing/blocking.",
                "Config rules to flag over-permissive SGs (e.g., open 22).",
            ]),
            ("h2", "Reliability"),
            ("bullets", [
                "SGs are enforced per-ENI in HA hardware; reliability is about correct rules.",
                "Avoid 'fix by opening 0/0' - it trades an outage for an exposure.",
            ]),
            ("h2", "Automation"),
            ("bullets", [
                "Define SGs + rules in IaC; use SG references for dynamic membership.",
                "Policy-as-code/Config to detect and auto-remediate risky rules.",
            ]),
        ]),
        ("Cost Considerations", [
            ("table", (COST_HDR, [
                ["Security groups", "Free - no charge for SGs or rules.",
                 "N/A; cost is operational (managing rule sprawl)."],
                ["Rule sprawl", "Indirect cost: errors, audits, incidents.",
                 "SG referencing + prefix lists to keep rules minimal."],
                ["Blocked-traffic debugging", "Engineer time on misconfig.",
                 "Reachability Analyzer + Flow Logs to cut MTTR."],
            ], COST_W)),
        ]),
        ("Troubleshooting Approach", [
            ("body", "For 'cannot connect to a resource':"),
            ("bullets", [
                "1. Which SGs are on the TARGET ENI, and do their INBOUND rules allow the "
                "source + port?",
                "2. Does the SOURCE's OUTBOUND allow it (if egress was tightened)?",
                "3. If using SG references, is the right SG referenced (and same VPC)?",
                "4. Remember SGs are stateful - don't chase return rules; check NACLs for "
                "those.",
                "5. Use Reachability Analyzer + Flow Log REJECTs.",
            ]),
            ("callout", ("Mnemonic", "'Target inbound -> Source outbound -> SG reference.' "
             "Statefulness means return traffic is not your problem here - that's a NACL "
             "concern.", GREEN)),
        ]),
        ("Real-World Examples & Patterns", [
            ("kv", [
                ("Tiered chaining", "web SG allows 443 from internet; app SG allows from web "
                 "SG; db SG allows 5432 from app SG."),
                ("Bastion-free admin", "No SSH SG to the world; use SSM Session Manager "
                 "instead."),
                ("Shared services", "Reference a central 'monitoring' SG to permit scraping "
                 "across fleets."),
                ("Microsegmentation", "Per-microservice SGs referencing each other for "
                 "least-privilege east-west traffic."),
            ]),
        ]),
        ("Senior-Level Trade-offs & Talking Points", [
            ("bullets", [
                "SG references (dynamic, scalable) vs CIDR rules (work across boundaries).",
                "Few broad SGs (simple) vs many fine SGs (least privilege, more management).",
                "SGs (stateful allow-only) vs NACLs (stateless allow/deny) - use both as "
                "layers.",
                "Tightening egress (security) vs operational friction (breaking app calls).",
            ]),
            ("callout", ("Whiteboard checklist",
             "(1) Draw ENI wrapped by SG. (2) Show inbound allow + stateful return. (3) Chain "
             "web->app->db via SG references. (4) Note default deny-in/allow-out. (5) Contrast "
             "with NACLs. (6) Discuss SG-ref scaling and exposure risks.")),
        ]),
        ("Quick Glossary", [
            ("table", (GLOS_HDR, [
                ["Security group", "Stateful, allow-only firewall on an ENI."],
                ["Stateful", "Return traffic for allowed flows is auto-permitted."],
                ["SG reference", "A rule whose source/dest is another security group."],
                ["Inbound/Outbound rules", "Separate allow lists per direction."],
                ["Default SG", "Allows all intra-SG traffic; deny-in/allow-out otherwise."],
                ["Prefix list", "Named, reusable set of CIDRs usable in SG rules."],
                ["ENI", "Elastic Network Interface the SG attaches to."],
            ], GLOS_W)),
        ]),
    ],
}


# --------------------------------------------------------------------------- #
# 6. NACLs
# --------------------------------------------------------------------------- #
def diagram_nacl(pdf):
    diagram_intro(
        pdf, "Reference Diagram - Stateless NACL at the subnet boundary",
        "A Network ACL is a stateless, ordered, allow/deny firewall evaluated at the "
        "SUBNET boundary. Because it is stateless, you must explicitly allow BOTH the "
        "request AND the return traffic - including ephemeral ports for responses.")
    top = pdf.get_y() + 4
    pdf.diag_box(LEFT, top, WIDTH, 40, (255, 255, 255), RED,
                 title="Network ACL (stateless, evaluated in rule-number order)",
                 title_color=RED)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*NAVY)
    cols = [(LEFT + 2, "Rule#"), (LEFT + 18, "Type"), (LEFT + 60, "Source/Dest"),
            (LEFT + 110, "Action")]
    ry = top + 8
    for cx, label in cols:
        pdf.set_xy(cx, ry); pdf.cell(40, 4, label)
    inrows = [
        ("100", "HTTPS 443 IN", "0.0.0.0/0", "ALLOW"),
        ("200", "Ephemeral 1024-65535 OUT", "0.0.0.0/0", "ALLOW"),
        ("*", "ALL", "0.0.0.0/0", "DENY"),
    ]
    ry += 5
    for num, typ, src, act in inrows:
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*(GREEN if act == "ALLOW" else RED))
        pdf.set_xy(LEFT + 2, ry); pdf.cell(16, 4, num)
        pdf.set_text_color(30, 30, 30)
        pdf.set_xy(LEFT + 18, ry); pdf.cell(42, 4, typ)
        pdf.set_xy(LEFT + 60, ry); pdf.cell(50, 4, src)
        pdf.set_text_color(*(GREEN if act == "ALLOW" else RED))
        pdf.set_xy(LEFT + 110, ry); pdf.cell(30, 4, act)
        ry += 5.2
    # subnet below
    sy = top + 46
    pdf.diag_box(LEFT + 20, sy, 130, 22, PRIVATE_FILL, BLUE,
                 title="Subnet 10.0.10.0/24", lines=["all ENIs in this subnet inherit the NACL"])
    pdf.diag_arrow(LEFT + 85, top + 40, LEFT + 85, sy, color=RED)
    pdf.diag_caption(
        LEFT, sy + 24, WIDTH,
        "Rules are processed lowest-number first; the first match wins, then evaluation "
        "stops. The final '*' rule denies anything unmatched. Forgetting the ephemeral-port "
        "ALLOW (rule 200) is the classic cause of one-way connectivity.")
    pdf.ln(2)


NACLS = {
    "title": "NACLs",
    "subtitle": "Stateless, Ordered Allow/Deny Filtering at the Subnet Boundary",
    "blurb": "Problem & motivation - statelessness & ordering - ephemeral ports - packet "
             "flow - failure modes - scaling - security - observability & automation - cost "
             "- troubleshooting - real-world patterns",
    "summary": (
        "A Network Access Control List (NACL) is a stateless, ordered firewall applied at "
        "the boundary of a subnet. Unlike security groups, NACLs evaluate numbered rules in "
        "order (first match wins), support both ALLOW and DENY, and - critically - are "
        "stateless, meaning you must allow the return traffic explicitly, including the "
        "ephemeral port range used for responses. NACLs act as a coarse, subnet-wide "
        "backstop beneath security groups and are the source of the single most common "
        "VPC connectivity bug. This guide covers internals, packet flow, failure modes, "
        "scaling, security, observability, automation, cost, and troubleshooting."),
    "sections": [
        ("The Problem It Solves", [
            ("body", "Sometimes you need a coarse, subnet-wide guardrail that can explicitly "
             "DENY traffic (e.g., block a malicious CIDR) independent of the many security "
             "groups inside that subnet. NACLs provide that subnet-level, deny-capable layer "
             "of defense in depth."),
            ("h2", "Core needs NACLs address"),
            ("kv", [
                ("Explicit deny", "Block specific IPs/ports that allow-only SGs cannot."),
                ("Subnet-wide backstop", "One coarse control covering every ENI in a subnet."),
                ("Defense in depth", "A second, independent layer beneath security groups."),
                ("Blast-radius limiting", "Contain compromised subnets at their boundary."),
            ]),
        ]),
        ("How It Works Internally", [
            ("body", "Each subnet is associated with exactly one NACL (the default NACL "
             "allows all). A NACL has separate, numbered inbound and outbound rule lists. "
             "For each packet crossing the subnet boundary, rules are evaluated from lowest "
             "number upward; the first match (ALLOW or DENY) is applied and evaluation "
             "stops. A final, un-editable '*' rule denies anything unmatched."),
            ("bullets", [
                "Stateless: the response to an allowed inbound request is NOT automatically "
                "allowed outbound - you must add an outbound rule (and vice versa).",
                "Responses use ephemeral source ports (typically 1024-65535), so return "
                "rules must allow that range.",
                "Lower rule numbers take precedence; leave gaps (100, 200, ...) for inserts.",
                "NACLs filter at the subnet edge; intra-subnet traffic between ENIs is not "
                "evaluated by the NACL.",
            ]),
            ("diagram", diagram_nacl),
        ]),
        ("Traffic Flow, Packet Flow & Routing Decisions", [
            ("h2", "Both directions must be allowed"),
            ("bullets", [
                "Inbound request to a subnet: inbound NACL rules checked in order; first "
                "match decides.",
                "The server's reply LEAVING the subnet is checked against OUTBOUND rules - "
                "must allow the client's ephemeral port range.",
                "For outbound-initiated flows, it is the reverse: outbound allows the "
                "request, inbound must allow the ephemeral return.",
                "NACLs are orthogonal to routing; they filter, they do not forward.",
            ]),
            ("callout", ("The ephemeral-port trap",
             "Allowing inbound 443 but forgetting an OUTBOUND allow for ports 1024-65535 "
             "means requests arrive but responses are dropped - classic one-way "
             "connectivity. Always pair request rules with ephemeral return rules.", RED)),
        ]),
        ("Advantages & Disadvantages", [
            ("h2", "Advantages"),
            ("bullets", [
                "Supports explicit DENY (blocklists) that SGs cannot.",
                "Subnet-wide coverage as a single coarse control.",
                "Independent second layer for defense in depth.",
                "Ordered rules give deterministic precedence.",
            ]),
            ("h2", "Disadvantages / costs"),
            ("bullets", [
                "Stateless - easy to break with missing ephemeral-port return rules.",
                "Coarse (subnet-level) - cannot express per-instance identity.",
                "Rule-count limits per NACL.",
                "Ordering mistakes silently change behavior.",
            ]),
        ]),
        ("Common Failure Modes", [
            ("table", (FAIL_HDR, [
                ["Missing ephemeral allow", "One-way / hangs", "Return ports 1024-65535 not "
                 "allowed on the opposite direction."],
                ["Rule-order mistake", "Wrong allow/deny applied", "A broad rule with a lower "
                 "number shadows a specific one."],
                ["Over-broad DENY", "Legit traffic blocked", "DENY rule too wide or "
                 "mis-numbered."],
                ["Wrong NACL assoc", "Unexpected block/allow", "Subnet associated with the "
                 "wrong NACL."],
                ["Forgot default deny", "False sense of security", "Assuming SG covers it; "
                 "NACL '*' denies unmatched."],
                ["Rule-limit hit", "Cannot add rule", "Too many entries; needs "
                 "consolidation."],
            ], FAIL_W)),
        ]),
        ("Scaling Considerations", [
            ("kv", [
                ("Keep them coarse", "Use NACLs for broad guardrails; do fine-grained work in "
                 "SGs."),
                ("Number with gaps", "Space rule numbers (100, 200) to insert later without "
                 "renumbering."),
                ("Consolidate", "Summarize CIDRs to stay within per-NACL rule limits."),
                ("Standardize", "Reuse a small set of vetted NACL templates across subnets."),
            ]),
        ]),
        ("Security Implications", [
            ("bullets", [
                "Use NACLs to block known-bad CIDRs at the subnet edge.",
                "Pair with security groups - NACL is the backstop, SG is the primary control.",
                "Beware: a too-strict NACL can break health checks and responses subtly.",
                "Document ephemeral-port rules so they are not 'cleaned up' by mistake.",
            ]),
        ]),
        ("Observability, Reliability & Automation", [
            ("h2", "Observability"),
            ("bullets", [
                "Flow Logs show REJECT - but note both SG and NACL can cause it; correlate.",
                "Reachability Analyzer flags NACL rules that block a path.",
            ]),
            ("h2", "Reliability"),
            ("bullets", [
                "Always include ephemeral-port return rules to avoid intermittent breakage.",
                "Change NACLs cautiously - they affect every ENI in the subnet at once.",
            ]),
            ("h2", "Automation"),
            ("bullets", [
                "Template NACLs in IaC with explicit ephemeral-port rules.",
                "Lint rules for ordering hazards and missing return ranges.",
            ]),
        ]),
        ("Cost Considerations", [
            ("table", (COST_HDR, [
                ["NACLs", "Free - no charge for NACLs or rules.",
                 "N/A; cost is operational risk from misconfiguration."],
                ["Outage risk", "Stateless mistakes cause incidents.",
                 "Standard templates + automated linting of ephemeral rules."],
                ["Debug time", "Hard-to-spot one-way failures.",
                 "Flow Logs correlation + Reachability Analyzer."],
            ], COST_W)),
        ]),
        ("Troubleshooting Approach", [
            ("body", "When connectivity is one-way or intermittent, suspect the NACL:"),
            ("bullets", [
                "1. Which NACL is on each subnet in the path?",
                "2. Inbound rules: is the request port allowed?",
                "3. Outbound rules: is the ephemeral return range (1024-65535) allowed?",
                "4. Check rule ORDER - is a lower-numbered rule shadowing the intended one?",
                "5. Correlate Flow Log REJECTs; remember SG vs NACL both can reject.",
            ]),
            ("callout", ("Mnemonic", "'Order -> Request -> Ephemeral return.' If SGs look "
             "fine but it's one-way, it's almost always a missing ephemeral NACL rule.",
             GREEN)),
        ]),
        ("Real-World Examples & Patterns", [
            ("kv", [
                ("Blocklist", "DENY a malicious CIDR at the subnet edge while SGs stay "
                 "allow-only."),
                ("Tier isolation", "Coarse NACLs reinforcing that data subnets only talk to "
                 "app subnets."),
                ("Default-allow + targeted deny", "Permissive NACL with a few high-priority "
                 "DENY rules."),
                ("Compliance backstop", "NACLs as an auditable, subnet-wide control layer."),
            ]),
        ]),
        ("Senior-Level Trade-offs & Talking Points", [
            ("bullets", [
                "NACLs (stateless, deny-capable, coarse) vs SGs (stateful, allow-only, "
                "fine) - layer them, don't choose one.",
                "Strict NACLs (more control) vs operational fragility (ephemeral-port "
                "breakage).",
                "Subnet-wide blast control vs inability to express per-instance identity.",
                "When to reach for AWS Network Firewall instead of complex NACLs.",
            ]),
            ("callout", ("Whiteboard checklist",
             "(1) Draw subnet boundary with NACL. (2) Show ordered numbered rules. (3) Add "
             "request + ephemeral return on opposite directions. (4) Note first-match-wins "
             "and '*' deny. (5) Contrast statefulness with SGs.")),
        ]),
        ("Quick Glossary", [
            ("table", (GLOS_HDR, [
                ["NACL", "Network ACL - stateless subnet-level allow/deny firewall."],
                ["Stateless", "Return traffic must be allowed explicitly."],
                ["Ephemeral ports", "High source ports (1024-65535) used by responses."],
                ["Rule number", "Determines evaluation order; lowest first, first match wins."],
                ["Default NACL", "Allows all traffic until you customize it."],
                ["'*' rule", "Final, un-editable DENY for unmatched traffic."],
                ["First-match-wins", "Evaluation stops at the first matching rule."],
            ], GLOS_W)),
        ]),
    ],
}


# --------------------------------------------------------------------------- #
# 7. TRANSIT GATEWAY
# --------------------------------------------------------------------------- #
def diagram_tgw(pdf):
    diagram_intro(
        pdf, "Reference Diagram - Transit Gateway hub-and-spoke",
        "A Transit Gateway (TGW) is a regional hub that connects many VPCs and on-prem "
        "networks through a single attachment per network, replacing an unmanageable mesh "
        "of peering connections. TGW route tables control which attachments can reach "
        "which.")
    top = pdf.get_y() + 6
    cx = LEFT + WIDTH / 2
    # central TGW
    tgw_w, tgw_h = 56, 16
    pdf.diag_box(cx - tgw_w / 2, top + 38, tgw_w, tgw_h, NAVY, NAVY)
    pdf.diag_label(cx - tgw_w / 2, top + 41, "Transit Gateway", color=(255, 255, 255),
                   bold=True, w=tgw_w, align="C", size=9)
    pdf.diag_label(cx - tgw_w / 2, top + 46, "(regional hub + route tables)",
                   color=(210, 220, 235), w=tgw_w, align="C", size=6.5)
    spokes = [
        (LEFT + 4, top, "VPC A 10.0.0.0/16", PRIVATE_FILL, BLUE),
        (LEFT + 60, top, "VPC B 10.1.0.0/16", PRIVATE_FILL, BLUE),
        (LEFT + 116, top, "VPC C 10.2.0.0/16", PRIVATE_FILL, BLUE),
        (LEFT + 4, top + 72, "On-prem (VPN)", PUBLIC_FILL, GREEN),
        (LEFT + 60, top + 72, "On-prem (DX)", PUBLIC_FILL, GREEN),
        (LEFT + 116, top + 72, "Shared svcs VPC", ISOLATED_FILL, ORANGE),
    ]
    for sx, sy, label, fill, edge in spokes:
        pdf.diag_box(sx, sy, 50, 16, fill, edge, title=label, title_size=7.5)
        # arrow to TGW
        ax = sx + 25
        ay = sy + (16 if sy < top + 38 else 0)
        pdf.diag_arrow(ax, ay, cx, top + 38 + (0 if sy < top + 38 else tgw_h),
                       color=GREY, width=0.3)
    pdf.diag_caption(
        LEFT, top + 92, WIDTH,
        "Each VPC/VPN/DX attaches ONCE to the TGW. TGW route tables segment reachability "
        "(e.g., spokes reach shared services but not each other). This replaces O(n^2) "
        "peering with O(n) attachments and supports transitive routing.")
    pdf.ln(2)


TRANSIT_GATEWAY = {
    "title": "Transit Gateway",
    "subtitle": "A Regional Hub for Scalable, Transitive Network Connectivity",
    "blurb": "Problem & motivation - attachments & route tables - transitive routing - "
             "packet flow - failure modes - scaling - security - observability & automation "
             "- cost - troubleshooting - real-world patterns",
    "summary": (
        "A Transit Gateway (TGW) is a regional network hub that interconnects VPCs, VPN "
        "connections, and Direct Connect gateways through a single attachment per network. "
        "It replaces the operationally explosive full-mesh of VPC peering (which is "
        "non-transitive and O(n^2)) with a hub-and-spoke model that supports transitive "
        "routing and segmentation via TGW route tables. TGW is the backbone of large "
        "multi-account, multi-VPC, hybrid architectures. This guide covers internals, "
        "packet flow, failure modes, scaling, security, observability, automation, cost, "
        "and troubleshooting."),
    "sections": [
        ("The Problem It Solves", [
            ("body", "VPC peering is simple for a few VPCs but does not scale: it is "
             "non-transitive (A-B and B-C does not give A-C) and the number of connections "
             "grows quadratically. Connecting dozens of VPCs and on-prem links by peering "
             "becomes an unmanageable mesh. A Transit Gateway centralizes this into one hub."),
            ("h2", "Core needs the TGW addresses"),
            ("kv", [
                ("Transitive routing", "Let any attached network reach any other (when "
                 "policy allows) through the hub."),
                ("Scale", "O(n) attachments instead of O(n^2) peerings."),
                ("Segmentation", "Use multiple TGW route tables to control who reaches whom."),
                ("Hybrid consolidation", "Terminate many VPN/DX connections at one hub."),
            ]),
        ]),
        ("How It Works Internally", [
            ("body", "A TGW is a regional, managed, horizontally scaled router. Networks "
             "connect via attachments (VPC, VPN, Direct Connect gateway, or peering to "
             "another TGW). The TGW maintains one or more TGW route tables; each attachment "
             "is associated with a route table and can propagate its routes into others. "
             "This association/propagation model is how you implement segmentation (e.g., "
             "isolated spokes that all reach shared services but not each other)."),
            ("bullets", [
                "VPC attachments place TGW ENIs in chosen subnets (ideally one per AZ) for "
                "the data path.",
                "Subnet route tables in each VPC send the relevant prefixes to the TGW "
                "attachment.",
                "TGW route tables then decide the next attachment (transitive routing).",
                "Inter-region peering connects TGWs across regions for a global backbone.",
            ]),
            ("diagram", diagram_tgw),
        ]),
        ("Traffic Flow, Packet Flow & Routing Decisions", [
            ("h2", "Packet from VPC A to VPC C via TGW"),
            ("bullets", [
                "Instance in VPC A sends to a VPC C address; SG egress evaluated.",
                "VPC A subnet route table: VPC C CIDR -> tgw attachment.",
                "Packet reaches the TGW; the attachment's associated TGW route table is "
                "consulted.",
                "TGW route table: VPC C CIDR -> VPC C attachment; packet forwarded.",
                "VPC C subnet route table must have a return route for VPC A via its TGW "
                "attachment.",
            ]),
            ("callout", ("Two-layer routing",
             "TGW connectivity requires BOTH the VPC subnet route tables (to/from the TGW) "
             "AND the TGW route tables (between attachments) to be correct - in both "
             "directions. Missing either layer breaks the path.", ORANGE)),
        ]),
        ("Advantages & Disadvantages", [
            ("h2", "Advantages"),
            ("bullets", [
                "Transitive, hub-and-spoke routing at scale.",
                "Segmentation via multiple route tables.",
                "Single place to terminate hybrid (VPN/DX) connectivity.",
                "Managed, HA, and inter-region capable.",
            ]),
            ("h2", "Disadvantages / costs"),
            ("bullets", [
                "Per-attachment hourly charge plus per-GB data processing.",
                "Adds a routing hop (latency) versus direct peering.",
                "Central hub is a logical concentration point - design for blast radius.",
                "Two-layer routing increases configuration complexity.",
            ]),
        ]),
        ("Common Failure Modes", [
            ("table", (FAIL_HDR, [
                ["Missing VPC route", "No reachability", "Subnet table lacks a route to the "
                 "TGW attachment."],
                ["TGW route gap", "Some pairs unreachable", "TGW route table missing the "
                 "destination attachment."],
                ["No propagation/assoc", "Segmentation wrong", "Attachment not associated/"
                 "propagated as intended."],
                ["CIDR overlap", "Ambiguous routing", "Two attached VPCs share a range."],
                ["Single-AZ attachment", "Partial outage", "TGW attachment ENI in too few "
                 "AZs."],
                ["Asymmetric path", "One-way", "Return-side VPC/TGW routes missing."],
            ], FAIL_W)),
        ]),
        ("Scaling Considerations", [
            ("kv", [
                ("Attachments not mesh", "Add VPCs as attachments; avoid peering sprawl."),
                ("Route-table design", "Use separate TGW route tables for prod/dev/shared "
                 "segmentation."),
                ("Per-AZ attachments", "Attach in every AZ you use for resilience and to "
                 "avoid cross-AZ hops."),
                ("Non-overlapping CIDRs", "Mandatory across all attached networks; use IPAM."),
                ("Bandwidth", "TGW scales horizontally; per-attachment/flow limits apply at "
                 "extreme scale."),
            ]),
        ]),
        ("Security Implications", [
            ("bullets", [
                "Use route-table segmentation as a security boundary (e.g., isolate spokes).",
                "Centralize egress/inspection by routing spokes through a firewall VPC via "
                "TGW.",
                "Remember TGW does not filter packets - rely on SGs/NACLs/firewall.",
                "Control attachment creation with IAM + RAM sharing in multi-account setups.",
            ]),
        ]),
        ("Observability, Reliability & Automation", [
            ("h2", "Observability"),
            ("bullets", [
                "TGW Flow Logs for inter-attachment traffic.",
                "CloudWatch metrics: bytes/packets in/out per attachment, drops.",
                "Network Manager to visualize the global topology.",
            ]),
            ("h2", "Reliability"),
            ("bullets", [
                "TGW is managed and HA within a region; attach across AZs.",
                "Use inter-region peering for cross-region resilience.",
            ]),
            ("h2", "Automation"),
            ("bullets", [
                "Manage attachments, route tables, associations, and propagations in IaC.",
                "Share TGW via Resource Access Manager across accounts programmatically.",
            ]),
        ]),
        ("Cost Considerations", [
            ("table", (COST_HDR, [
                ["Attachment-hours", "Each attachment bills per hour.",
                 "Consolidate; remove unused attachments."],
                ["Data processing", "Per-GB through the TGW.",
                 "Keep chatty workloads in one VPC; use endpoints for AWS services."],
                ["Cross-AZ/region", "Extra transfer for non-local paths.",
                 "Per-AZ attachments; mind inter-region peering costs."],
            ], COST_W)),
        ]),
        ("Troubleshooting Approach", [
            ("body", "For 'VPC A cannot reach VPC C via TGW':"),
            ("bullets", [
                "1. VPC A subnet route: destination CIDR -> TGW attachment?",
                "2. TGW route table for A's attachment: route to C's attachment?",
                "3. Association/propagation set so the route exists where needed?",
                "4. Return path: C's subnet + TGW routes back to A?",
                "5. No CIDR overlap; confirm with Network Manager / Reachability Analyzer.",
            ]),
            ("callout", ("Mnemonic", "'VPC route -> TGW route -> Assoc/Prop -> Return.' "
             "Always verify BOTH the VPC layer and the TGW layer, in BOTH directions.",
             GREEN)),
        ]),
        ("Real-World Examples & Patterns", [
            ("kv", [
                ("Hub-and-spoke", "Many app VPCs attach to one TGW; a shared-services VPC is "
                 "reachable by all."),
                ("Segmented spokes", "Separate TGW route tables so spokes reach shared "
                 "services but not each other."),
                ("Centralized egress", "Spokes route 0/0 to TGW -> egress VPC with NAT + "
                 "firewall."),
                ("Global backbone", "Inter-region TGW peering links regional hubs; on-prem "
                 "via DX gateway."),
            ]),
        ]),
        ("Senior-Level Trade-offs & Talking Points", [
            ("bullets", [
                "TGW (scalable, transitive, segmented) vs peering (lower latency/cost, "
                "non-transitive) - choose by VPC count and topology.",
                "Central hub simplicity vs blast-radius/bottleneck concentration.",
                "Per-AZ attachments (resilient, no cross-AZ fees) vs fewer attachments "
                "(cheaper, riskier).",
                "Centralized inspection via TGW vs distributed controls.",
            ]),
            ("callout", ("Whiteboard checklist",
             "(1) Draw TGW hub with VPC/VPN/DX spokes. (2) Show single attachment each. (3) "
             "Two-layer routing (VPC + TGW tables). (4) Segment with route tables. (5) "
             "Discuss transitivity, cost (attachment + per-GB), and CIDR planning.")),
        ]),
        ("Quick Glossary", [
            ("table", (GLOS_HDR, [
                ["Transit Gateway", "Regional hub interconnecting VPCs and on-prem."],
                ["Attachment", "A network's single connection to the TGW (VPC/VPN/DX/peer)."],
                ["TGW route table", "Controls which attachment reaches which (segmentation)."],
                ["Association", "Binds an attachment to a TGW route table."],
                ["Propagation", "Injects an attachment's routes into a TGW route table."],
                ["Transitive routing", "A can reach C through the hub via B-less topology."],
                ["Inter-region peering", "Connecting TGWs across regions."],
            ], GLOS_W)),
        ]),
    ],
}


# --------------------------------------------------------------------------- #
# 8. DIRECT CONNECT
# --------------------------------------------------------------------------- #
def diagram_dx(pdf):
    diagram_intro(
        pdf, "Reference Diagram - Direct Connect private link to AWS",
        "AWS Direct Connect (DX) is a dedicated, private physical network link between your "
        "data center and AWS, bypassing the public internet for consistent bandwidth and "
        "lower, more predictable latency. Logical Virtual Interfaces (VIFs) ride the "
        "physical link.")
    top = pdf.get_y() + 6
    # on-prem
    pdf.diag_box(LEFT, top + 18, 44, 26, PUBLIC_FILL, GREEN,
                 title="On-prem DC", lines=["customer router", "192.168.0.0/16"])
    # DX location
    pdf.diag_box(LEFT + 58, top + 14, 54, 34, (255, 255, 255), NAVY,
                 title="DX Location", lines=["cross-connect", "AWS DX router", "+ customer cage"])
    # AWS region
    pdf.diag_box(LEFT + 124, top, WIDTH - 124 - 0 + LEFT - LEFT, 62, (245, 248, 252), NAVY,
                 title="AWS Region", title_size=8)
    pdf.diag_box(LEFT + 128, top + 12, 38, 18, PRIVATE_FILL, BLUE,
                 title="VPC (VGW", lines=["/ DXGW)"])
    pdf.diag_box(LEFT + 128, top + 34, 38, 16, ISOLATED_FILL, ORANGE,
                 title="Public AWS", lines=["S3, public APIs"])
    # links
    pdf.diag_arrow(LEFT + 44, top + 30, LEFT + 58, top + 30, color=GREY, width=0.6)
    pdf.diag_arrow(LEFT + 112, top + 24, LEFT + 128, top + 20, color=BLUE)
    pdf.diag_label(LEFT + 112, top + 16, "Private VIF", color=BLUE, size=6.5, w=20)
    pdf.diag_arrow(LEFT + 112, top + 40, LEFT + 128, top + 42, color=ORANGE)
    pdf.diag_label(LEFT + 113, top + 44, "Public VIF", color=ORANGE, size=6.5, w=24)
    pdf.diag_caption(
        LEFT, top + 64, WIDTH,
        "A private VIF reaches VPCs (via a Virtual Private Gateway or Direct Connect "
        "Gateway); a public VIF reaches AWS public services; a transit VIF reaches a "
        "Transit Gateway. BGP exchanges routes. Provisioning takes weeks (physical "
        "cross-connect), so a VPN backup is standard.")
    pdf.ln(2)


DIRECT_CONNECT = {
    "title": "Direct Connect",
    "subtitle": "Dedicated, Private Physical Connectivity Between On-Prem and AWS",
    "blurb": "Problem & motivation - VIFs & BGP - resiliency models - packet flow - failure "
             "modes - scaling - security - observability & automation - cost - "
             "troubleshooting - real-world patterns",
    "summary": (
        "AWS Direct Connect (DX) provides a dedicated, private physical network connection "
        "between an on-premises data center and AWS, bypassing the public internet. It "
        "delivers consistent bandwidth, lower and more predictable latency, and reduced "
        "data-transfer-out costs at scale. Logical Virtual Interfaces (private, public, or "
        "transit) ride over the physical link, exchanging routes via BGP. Because DX is "
        "physical, it has long lead times and must be paired with redundancy (a second DX "
        "or a VPN backup) for production. This guide covers internals, packet flow, failure "
        "modes, scaling, security, observability, automation, cost, and troubleshooting."),
    "sections": [
        ("The Problem It Solves", [
            ("body", "Internet-based VPN connectivity to AWS rides shared, best-effort "
             "internet paths with variable latency, jitter, and throughput, and incurs "
             "internet data-transfer charges. Workloads that need consistent performance, "
             "high sustained bandwidth, or lower egress cost need a dedicated path - that is "
             "Direct Connect."),
            ("h2", "Core needs DX addresses"),
            ("kv", [
                ("Consistent performance", "Dedicated bandwidth with predictable, low "
                 "latency - not best-effort internet."),
                ("High throughput", "1/10/100 Gbps dedicated, or sub-1G hosted connections."),
                ("Lower egress cost", "Reduced data-transfer-out rates vs internet at scale."),
                ("Private reachability", "Reach VPCs and AWS public services without "
                 "traversing the public internet."),
            ]),
        ]),
        ("How It Works Internally", [
            ("body", "You establish a cross-connect at a Direct Connect location between your "
             "router (in a colo cage or via a partner) and an AWS DX router. Over that "
             "physical port you create Virtual Interfaces (VIFs): a PRIVATE VIF to reach "
             "VPCs (through a Virtual Private Gateway or a Direct Connect Gateway), a PUBLIC "
             "VIF to reach AWS public services (e.g., S3) over the private link, or a "
             "TRANSIT VIF to reach a Transit Gateway. BGP sessions exchange routes between "
             "your network and AWS."),
            ("bullets", [
                "Dedicated connection: a physical AWS port (1/10/100 Gbps). Hosted "
                "connection: capacity provisioned via a partner (often sub-1G).",
                "A Direct Connect Gateway lets one VIF reach VPCs in multiple regions/"
                "accounts.",
                "BGP advertises your on-prem prefixes to AWS and AWS/VPC prefixes to you.",
                "DX is NOT encrypted by itself - layer IPsec/MACsec for confidentiality.",
            ]),
            ("diagram", diagram_dx),
        ]),
        ("Traffic Flow, Packet Flow & Routing Decisions", [
            ("h2", "On-prem to VPC over a private VIF"),
            ("bullets", [
                "On-prem host -> customer router; BGP has learned the VPC CIDR via DX.",
                "Traffic crosses the cross-connect to the AWS DX router over the private VIF.",
                "Routed via VGW/DX Gateway into the target VPC; VPC route tables carry the "
                "on-prem prefix back via the gateway.",
                "Security groups/NACLs apply inside the VPC as usual.",
                "Return traffic follows BGP-learned routes back over DX.",
            ]),
            ("callout", ("Routing preference & resiliency",
             "When both DX and a VPN exist, BGP normally prefers DX; the VPN takes over on "
             "DX failure. Tune BGP (AS-path prepend, local pref, MED) for deterministic "
             "primary/backup behavior.", ORANGE)),
        ]),
        ("Advantages & Disadvantages", [
            ("h2", "Advantages"),
            ("bullets", [
                "Consistent, low-latency, high-bandwidth private connectivity.",
                "Lower data-transfer-out cost than internet at scale.",
                "Reaches VPCs (multi-region via DX Gateway) and AWS public services.",
                "Avoids the public internet entirely for the transport.",
            ]),
            ("h2", "Disadvantages / costs"),
            ("bullets", [
                "Long lead time (physical cross-connect) - provisioning takes weeks.",
                "Single DX is a SPOF; true resiliency needs redundant links/locations.",
                "Not encrypted by default - add IPsec/MACsec.",
                "Port-hour + data-transfer charges, plus colo/partner costs.",
            ]),
        ]),
        ("Common Failure Modes", [
            ("table", (FAIL_HDR, [
                ["Single DX SPOF", "Total hybrid outage", "No redundant connection or VPN "
                 "backup."],
                ["BGP misconfig", "No/partial routes", "Wrong ASN, prefixes not advertised, "
                 "or filters."],
                ["No encryption", "Compliance gap", "Assuming DX is private == encrypted."],
                ["MTU mismatch", "Fragmentation/drops", "Jumbo-frame settings inconsistent."],
                ["VIF/gateway gap", "VPC unreachable", "Private VIF not associated with "
                 "VGW/DXGW correctly."],
                ["Asymmetric routing", "One-way", "DX in, VPN out (or vice versa) due to "
                 "route preference."],
            ], FAIL_W)),
        ]),
        ("Scaling Considerations", [
            ("kv", [
                ("Redundancy", "Two connections at two DX locations (and/or VPN backup) for "
                 "production SLAs."),
                ("LAG", "Aggregate multiple ports into a Link Aggregation Group for more "
                 "bandwidth."),
                ("DX Gateway", "Reach many VPCs across regions/accounts from one connection."),
                ("Transit VIF + TGW", "Scale to many VPCs via a Transit Gateway instead of "
                 "per-VPC private VIFs."),
                ("Capacity planning", "Choose dedicated (1/10/100G) vs hosted based on "
                 "sustained throughput."),
            ]),
        ]),
        ("Security Implications", [
            ("bullets", [
                "DX is private transport but NOT encrypted - add IPsec VPN over DX or MACsec.",
                "Filter BGP advertisements to avoid leaking/accepting unintended routes.",
                "Apply SGs/NACLs inside the VPC; DX does not filter traffic.",
                "Protect the physical/colo footprint and partner relationships.",
            ]),
        ]),
        ("Observability, Reliability & Automation", [
            ("h2", "Observability"),
            ("bullets", [
                "CloudWatch DX metrics: ConnectionState, BGP state, light levels, in/out "
                "bps, error counts.",
                "Alarm on BGP session down and link/light degradation.",
            ]),
            ("h2", "Reliability"),
            ("bullets", [
                "Design to AWS's resiliency models (redundant connections/locations).",
                "Maintain a VPN failover and test it; tune BGP for clean failover.",
            ]),
            ("h2", "Automation"),
            ("bullets", [
                "Manage VIFs, DX Gateway, and associations in IaC where supported.",
                "Automated BGP/route monitoring and failover tests.",
            ]),
        ]),
        ("Cost Considerations", [
            ("table", (COST_HDR, [
                ["Port-hours", "Charged per hour for the connection capacity.",
                 "Right-size capacity; use hosted for smaller needs."],
                ["Data transfer out", "Lower DX rate, but still per-GB.",
                 "Route bulk egress over DX vs internet at scale."],
                ["Redundancy", "Second link/location multiplies cost.",
                 "Balance SLA vs cost; VPN backup is cheaper than dual DX."],
            ], COST_W)),
        ]),
        ("Troubleshooting Approach", [
            ("body", "For 'on-prem cannot reach the VPC over DX':"),
            ("bullets", [
                "1. Physical/port: is the connection 'up' and light levels healthy?",
                "2. BGP: are sessions established and the right prefixes advertised/received?",
                "3. VIF: correct type and associated with VGW/DXGW/TGW?",
                "4. VPC routes: do subnet tables carry the on-prem prefix via the gateway?",
                "5. Return path & preference: is routing symmetric (DX vs VPN)? Check MTU.",
            ]),
            ("callout", ("Mnemonic", "'Port -> BGP -> VIF -> VPC routes -> Symmetry.' Most DX "
             "issues are BGP advertisement/preference or a missing VIF-to-gateway "
             "association.", GREEN)),
        ]),
        ("Real-World Examples & Patterns", [
            ("kv", [
                ("Dual DX", "Two connections at two locations for high resiliency."),
                ("DX + VPN backup", "DX primary with an IPsec VPN failover (cost-effective "
                 "resiliency)."),
                ("Encrypted DX", "IPsec/MACsec over DX for confidentiality + compliance."),
                ("DX Gateway + TGW", "One link reaching many VPCs/regions via transit VIF + "
                 "Transit Gateway."),
            ]),
        ]),
        ("Senior-Level Trade-offs & Talking Points", [
            ("bullets", [
                "DX (consistent, private, costly, slow to provision) vs VPN (fast, cheap, "
                "internet-variable).",
                "Dedicated vs hosted connections: capacity/control vs speed-to-provision.",
                "Dual DX (highest SLA) vs DX + VPN backup (cost-effective resiliency).",
                "Encryption overhead vs compliance requirements over a 'private' link.",
            ]),
            ("callout", ("Whiteboard checklist",
             "(1) Draw on-prem -> DX location cross-connect -> AWS. (2) Show private/public/"
             "transit VIFs. (3) BGP route exchange. (4) Add VPN backup + BGP preference. "
             "(5) Note no default encryption. (6) Discuss resiliency models and cost.")),
        ]),
        ("Quick Glossary", [
            ("table", (GLOS_HDR, [
                ["Direct Connect", "Dedicated private physical link from on-prem to AWS."],
                ["VIF", "Virtual Interface (private/public/transit) over the DX link."],
                ["Private VIF", "Reaches VPCs via a VGW or Direct Connect Gateway."],
                ["Public VIF", "Reaches AWS public services over the private link."],
                ["DX Gateway", "Connects a VIF to VPCs across regions/accounts."],
                ["LAG", "Link Aggregation Group bundling multiple ports."],
                ["BGP", "Routing protocol exchanging prefixes between on-prem and AWS."],
            ], GLOS_W)),
        ]),
    ],
}


TOPICS = [
    ("Subnets", SUBNETS),
    ("Route_Tables", ROUTE_TABLES),
    ("Internet_Gateway", INTERNET_GATEWAY),
    ("NAT_Gateway", NAT_GATEWAY),
    ("Security_Groups", SECURITY_GROUPS),
    ("NACLs", NACLS),
    ("Transit_Gateway", TRANSIT_GATEWAY),
    ("Direct_Connect", DIRECT_CONNECT),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for key, topic in TOPICS:
        out = os.path.join(OUT_DIR, f"{key}_Interview_Guide.pdf")
        pages = build_pdf(topic, out)
        print(f"WROTE {out}  ({pages} pages)")


if __name__ == "__main__":
    main()
