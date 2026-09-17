import { AppShell } from "@/components/layout/AppShell"
import { Card, CardContent } from "@/components/ui/Card"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"
import { currentStudent, currentTeacher, studentCourses, teacherCourses } from "@/data/mockData"
import type { Role } from "@/types"

export default function Settings({ role }: { role: Role }) {
  const user = role === "student" ? currentStudent : currentTeacher
  const courses = role === "student" ? studentCourses : teacherCourses

  return (
    <AppShell
      role={role}
      userName={user.name}
      userEmail={user.email}
      courses={courses}
      crumbs={[{ label: role === "student" ? "Home" : "Dashboard", to: role === "student" ? "/student" : "/teacher" }, { label: "Settings" }]}
    >
      <Card className="max-w-lg">
        <CardContent className="space-y-4">
          <h1 className="text-lg font-semibold text-[var(--color-ink)]">Account settings</h1>
          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--color-ink-soft)]">Name</label>
            <Input defaultValue={user.name} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--color-ink-soft)]">Email</label>
            <Input defaultValue={user.email} type="email" />
          </div>
          <Button>Save changes</Button>
        </CardContent>
      </Card>
    </AppShell>
  )
}
