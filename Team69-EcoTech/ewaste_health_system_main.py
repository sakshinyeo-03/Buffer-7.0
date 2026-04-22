"""
=============================================================
  GreenTech E-Waste Component Health Evaluation System
  — Excel Input Edition —
=============================================================
  HOW TO USE:
    python ewaste_health_system.py                        <- uses drive_input_template.xlsx
    python ewaste_health_system.py my_drives.xlsx         <- uses your own file

  EXCEL SHEET COLUMNS REQUIRED:
    serial_no | type | capacity_gb | reallocated_sector_count
    | power_on_hours | spin_retry_count | temperature_celsius

  DSA Concepts:
    Stage 1 — Hash Map      : Identification & Tracking
    Stage 2 — Decision Tree : Diagnosis & Health Scoring
    Stage 3 — Linked List   : Virtual Repair (Bad Sector Bypass)
    Stage 4 — Max-Heap      : Strategic Allocation
=============================================================
"""

import sys
import heapq
import pandas as pd


# -----------------------------------------------------------------
# EXCEL LOADER — reads the input sheet into Component objects
# -----------------------------------------------------------------

REQUIRED_COLUMNS = [
    "serial_no",
    "type",
    "capacity_gb",
    "reallocated_sector_count",
    "power_on_hours",
    "spin_retry_count",
    "temperature_celsius",
]

def load_from_excel(filepath: str) -> list:
    """
    Reads the Excel sheet and returns a list of Component objects.
    Each row -> one Component whose .data dict is the Hash Map (Stage 1).
    """
    try:
        # Try reading with default header first
        df_probe = pd.read_excel(filepath, nrows=5)
        cols = [str(c).strip().lower() for c in df_probe.columns]

        if "serial_no" in cols:
            # Standard flat sheet — headers on row 1
            df = pd.read_excel(filepath, dtype={"serial_no": str, "type": str})
        else:
            # GreenTech template — headers on row 3, hint row on row 4 -> skip it
            df = pd.read_excel(filepath, header=2, skiprows=[3],
                               dtype={"serial_no": str, "type": str})
    except FileNotFoundError:
        print(f"\n   ERROR: File '{filepath}' not found.")
        print("     Please place your Excel file in the same folder as this script.\n")
        sys.exit(1)

    # Normalise column names (strip whitespace, lowercase)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        print(f"\n   ERROR: Missing columns in Excel sheet: {missing}")
        print(f"     Required columns: {REQUIRED_COLUMNS}\n")
        sys.exit(1)

    # Drop completely empty rows
    df = df.dropna(subset=["serial_no"])

    components = []
    for _, row in df.iterrows():
        comp = Component(
            serial_no               = str(row["serial_no"]).strip(),
            comp_type               = str(row["type"]).strip().upper(),
            capacity_gb             = int(row["capacity_gb"]),
            bad_sectors             = int(row["reallocated_sector_count"]),
            power_on_hours          = int(row["power_on_hours"]),
            spin_retry_count        = int(row["spin_retry_count"]),
            temperature_celsius     = float(row["temperature_celsius"]),
        )
        components.append(comp)

    print(f"   Loaded {len(components)} drive(s) from '{filepath}'\n")
    return components


# -----------------------------------------------------------------
# STAGE 1: IDENTIFICATION & TRACKING — Hash Map
# -----------------------------------------------------------------

class Component:
    """
    Represents one salvaged drive.
    All attributes stored as a Hash Map (Python dict) -> O(1) access.
    """

    def __init__(self, serial_no, comp_type, capacity_gb,
                 bad_sectors, power_on_hours, spin_retry_count,
                 temperature_celsius):

        # DSA — Hash Map: key-value pairs for instant O(1) lookup
        self.data = {
            "serial_no"                 : serial_no,
            "type"                      : comp_type,
            "capacity_gb"               : capacity_gb,
            "reallocated_sector_count"  : bad_sectors,
            "power_on_hours"            : power_on_hours,
            "spin_retry_count"          : spin_retry_count,
            "temperature_celsius"       : temperature_celsius,
        }

        self.health_score  = 0      # Set in Stage 2
        self.category      = ""     # Set in Stage 2
        self.usable_blocks = None   # Set in Stage 3

    def get(self, key):
        """O(1) Hash Map lookup."""
        return self.data.get(key)

    def __repr__(self):
        return (f"[{self.get('serial_no')}] "
                f"Health={self.health_score:.1f}% | "
                f"Category={self.category} | "
                f"Cap={self.get('capacity_gb')}GB")


# -----------------------------------------------------------------
# STAGE 2: DIAGNOSTIC BRAIN — Weighted Decision Tree
# -----------------------------------------------------------------

class DecisionTreeNode:
    """One node in the weighted decision tree."""
    def __init__(self, attribute, threshold, weight,
                 yes_node=None, no_node=None, result=None):
        self.attribute = attribute
        self.threshold = threshold
        self.weight    = weight
        self.yes_node  = yes_node
        self.no_node   = no_node
        self.result    = result   # Only set on leaf nodes


def build_decision_tree():
    """
    Weighted Decision Tree structure (most critical factor at root):

    Root  [w=50]: reallocated_sector_count > 50?
      YES -> Recycle  (physical damage — fatal)
      NO  -> [w=30]: power_on_hours > 20000?
              YES -> Secondary
              NO  -> [w=15]: spin_retry_count > 5?
                      YES -> Secondary
                      NO  -> [w=5]: temperature_celsius > 50?
                                YES -> Secondary
                                NO  -> Premium
    """
    recycle_leaf   = DecisionTreeNode(None, None, 0, result="Recycle")
    secondary_leaf = DecisionTreeNode(None, None, 0, result="Secondary")
    premium_leaf   = DecisionTreeNode(None, None, 0, result="Premium")

    temp_node = DecisionTreeNode(
        "temperature_celsius", 50, 5,
        yes_node=secondary_leaf, no_node=premium_leaf
    )
    spin_node = DecisionTreeNode(
        "spin_retry_count", 5, 15,
        yes_node=secondary_leaf, no_node=temp_node
    )
    hours_node = DecisionTreeNode(
        "power_on_hours", 20000, 30,
        yes_node=secondary_leaf, no_node=spin_node
    )
    root = DecisionTreeNode(
        "reallocated_sector_count", 50, 50,
        yes_node=recycle_leaf, no_node=hours_node
    )
    return root


def calculate_health_score(component):
    """
    Computes a 0-100 health score using weighted penalties, then
    traverses the decision tree to assign a category label.
    """
    bad_sec = component.get("reallocated_sector_count")
    hours   = component.get("power_on_hours")
    spin    = component.get("spin_retry_count")
    temp    = component.get("temperature_celsius")

    penalty  = 0
    penalty += min(50, (bad_sec / 50)  * 50)   # Up to 50 pts — physical wear
    penalty += min(30, (hours  / 20000)* 30)   # Up to 30 pts — age
    penalty += min(15, (spin   / 5)    * 15)   # Up to 15 pts — reliability
    penalty += min(5,  (temp   / 50)   * 5)    # Up to  5 pts — temperature

    health_score = max(0.0, 100.0 - penalty)

    # Traverse tree for category
    node = build_decision_tree()
    while node.result is None:
        value = component.get(node.attribute)
        node = node.yes_node if value > node.threshold else node.no_node

    return round(health_score, 2), node.result


def diagnose(component):
    """Runs Stage 2 and updates component in place."""
    score, category = calculate_health_score(component)
    component.health_score = score
    component.category     = category


# -----------------------------------------------------------------
# STAGE 3: VIRTUAL REPAIR — Singly Linked List
# -----------------------------------------------------------------
#
# WHY A LINKED LIST WORKS HERE:
#   A hard disk's sectors are conceptually sequential (like a chain).
#   When a sector goes bad, we don't delete it — we just re-link the
#   pointer of the previous block to skip over the corrupt one.
#   This mirrors how real OS bad-sector management works at a high level.
#
# KEY OPERATION: pointer bypass -> O(n) single pass, no shifting needed
# (Unlike arrays where removing an element requires shifting everything.)
# -----------------------------------------------------------------

class BlockNode:
    """One storage block (sector) on the disk."""
    def __init__(self, block_id, is_corrupt=False):
        self.block_id   = block_id
        self.is_corrupt = is_corrupt
        self.next       = None


class DiskLinkedList:
    """
    Simulates a disk's storage as a Singly Linked List.
    Corrupt blocks are bypassed via pointer manipulation.
    """
    def __init__(self, total_blocks):
        self.total = total_blocks
        self.head  = None
        self._build(total_blocks)

    def _build(self, n):
        dummy = BlockNode(-1)
        cur   = dummy
        for i in range(n):
            cur.next = BlockNode(i)
            cur = cur.next
        self.head = dummy.next

    def mark_corrupt(self, corrupt_ids: list):
        cur = self.head
        while cur:
            if cur.block_id in corrupt_ids:
                cur.is_corrupt = True
            cur = cur.next

    def bypass_corrupt_blocks(self):
        """
        DSA Core — Linked List pointer manipulation.
        Re-links prev -> next.next to skip corrupt nodes.
        Time: O(n)
        """
        bypassed = []
        dummy    = BlockNode(-1)
        dummy.next = self.head
        prev, cur = dummy, self.head

        while cur:
            if cur.is_corrupt:
                bypassed.append(cur.block_id)
                prev.next = cur.next      # Skip the corrupt node
            else:
                prev = cur
            cur = cur.next

        self.head = dummy.next
        return bypassed

    def usable_count(self):
        count, cur = 0, self.head
        while cur:
            count += 1
            cur = cur.next
        return count


def virtual_repair(component, total_blocks=20):
    """
    Simulates bad-sector bypass using a Singly Linked List.
    Corrupt block IDs are derived from the component's bad_sector count.
    """
    bad = component.get("reallocated_sector_count")
    # Spread corrupt blocks proportionally across the simulated disk
    if bad == 0:
        corrupt_ids = []
    else:
        step = max(1, total_blocks // max(bad, 1))
        corrupt_ids = list(range(0, min(bad, total_blocks), step))

    disk = DiskLinkedList(total_blocks)
    disk.mark_corrupt(corrupt_ids)
    bypassed = disk.bypass_corrupt_blocks()
    component.usable_blocks = disk.usable_count()
    return disk, bypassed


# -----------------------------------------------------------------
# STAGE 4: STRATEGIC ALLOCATION — Max-Heap
# -----------------------------------------------------------------

class AllocationHeap:
    """
    Max-Heap where priority = health_score x capacity_gb.
    Python's heapq is min-heap -> store negated priorities.
    """
    def __init__(self):
        self._heap    = []
        self._counter = 0

    def push(self, component):
        priority = component.health_score * component.get("capacity_gb")
        heapq.heappush(self._heap, (-priority, self._counter, component))
        self._counter += 1

    def pop(self):
        """O(log n) — returns highest-priority component."""
        if self._heap:
            neg_p, _, comp = heapq.heappop(self._heap)
            return comp, -neg_p
        return None, 0

    def size(self):
        return len(self._heap)


# -----------------------------------------------------------------
# MAIN PIPELINE
# -----------------------------------------------------------------

def run_pipeline(components: list):
    print("=" * 62)
    print("   GreenTech E-Waste Health Evaluation System")
    print("=" * 62)

    premium_heap   = AllocationHeap()
    secondary_list = []
    recycle_list   = []

    for comp in components:
        serial = comp.get("serial_no")
        print(f"\n{'─'*58}")
        print(f"    PROCESSING: {serial}  ({comp.get('type')} | {comp.get('capacity_gb')} GB)")
        print(f"{'─'*58}")

        # -- Stage 1 --
        print("  [Stage 1 - Hash Map] Attributes stored & retrieved in O(1):")
        for k, v in comp.data.items():
            print(f"     {k:<30} = {v}")

        # -- Stage 2 --
        diagnose(comp)
        print(f"\n  [Stage 2 - Decision Tree] Diagnosis result:")
        print(f"     Health Score : {comp.health_score}%")
        print(f"     Category     : {comp.category}")

        # -- Stage 3 --
        total_blocks = 20
        if comp.category in ("Premium", "Secondary"):
            disk, bypassed = virtual_repair(comp, total_blocks)
            usable = disk.usable_count()
            print(f"\n  [Stage 3 - Linked List] Virtual Repair Simulation:")
            print(f"     Total Blocks   : {total_blocks}")
            print(f"     Usable Blocks  : {usable} / {total_blocks}  "
                  f"({'Safe for use' if usable >= 18 else 'Limited capacity'})")
        else:
            print(f"\n  [Stage 3 - Linked List] Skipped - drive sent directly to Recycle")

        # -- Stage 4 --
        if comp.category == "Premium":
            premium_heap.push(comp)
            score = comp.health_score * comp.get("capacity_gb")
            print(f"\n  [Stage 4 - Max-Heap] Inserted into Premium queue.")
            print(f"     Priority Score : {score:.1f}  (health x capacity)")
        elif comp.category == "Secondary":
            secondary_list.append(comp)
            print(f"\n  [Stage 4] Added to Secondary use list.")
        else:
            recycle_list.append(comp)
            print(f"\n  [Stage 4] Sent to Recycle")

    # -- Final Report --
    print(f"\n{'='*62}")
    print("   ALLOCATION REPORT  (Max-Heap -> best drive first)")
    print(f"{'='*62}")

    print("\n    PREMIUM REUSE - ranked by Priority Score:")
    rank = 1
    while premium_heap.size() > 0:
        comp, score = premium_heap.pop()
        print(f"     #{rank}  {comp}  |  Score: {score:.1f}")
        rank += 1
    if rank == 1:
        print("     (none)")

    print("\n     SECONDARY USE:")
    if secondary_list:
        for comp in secondary_list:
            print(f"     ->  {comp}")
    else:
        print("     (none)")

    print("\n     RECYCLE:")
    if recycle_list:
        for comp in recycle_list:
            print(f"     ->  {comp}")
    else:
        print("     (none)")

    total = len(components)
    p_cnt = rank - 1
    s_cnt = len(secondary_list)
    r_cnt = len(recycle_list)

    print(f"\n{'='*62}")
    print("   SUMMARY")
    print(f"{'='*62}")
    print(f"   Total drives processed : {total}")
    print(f"   Premium reuse          : {p_cnt}  ({p_cnt/total*100:.0f}%)")
    print(f"   Secondary use          : {s_cnt}  ({s_cnt/total*100:.0f}%)")
    print(f"   Recycled               : {r_cnt}  ({r_cnt/total*100:.0f}%)")
    print()


# -----------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------

if __name__ == "__main__":
    # Accept filename as command-line argument, default to template
    excel_file = sys.argv[1] if len(sys.argv) > 1 else "drive_input_template.xlsx"

    print(f"\n   Reading input from: {excel_file}")
    components = load_from_excel(excel_file)
    run_pipeline(components)
