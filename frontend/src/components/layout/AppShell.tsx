import { useState, type ReactNode } from "react"
import { Sidebar } from "./Sidebar"
import { PageHeader } from "./PageHeader"
import type { Course, Role } from "@/types"

export function AppShell({
  role,
  userName,
  userEmail,
  courses,
  crumbs,
  search,
  headerRight,
  children,
}: {
  role: Role
  userName: string
  userEmail: string
  courses: Course[]
  crumbs: { label: string; to?: string }[]
  search?: string
  headerRight?: ReactNode
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-[var(--color-canvas)]">
      <Sidebar role={role} userName={userName} userEmail={userEmail} courses={courses} open={open} onClose={() => setOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <PageHeader crumbs={crumbs} search={search} onMenuClick={() => setOpen(true)} right={headerRight} />
        <main className="flex-1 p-4 lg:p-8">{children}</main>
      </div>
    </div>
  )
}
