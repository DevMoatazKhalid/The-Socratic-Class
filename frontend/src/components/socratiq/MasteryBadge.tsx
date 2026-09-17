import { Badge } from "@/components/ui/Badge"
import type { StudentRow } from "@/types"

const tone: Record<StudentRow["mastery"], "success" | "slate" | "danger"> = {
  Strong: "success",
  Moderate: "slate",
  Weak: "danger",
}

export function MasteryBadge({ level }: { level: StudentRow["mastery"] }) {
  return <Badge tone={tone[level]}>{level}</Badge>
}
