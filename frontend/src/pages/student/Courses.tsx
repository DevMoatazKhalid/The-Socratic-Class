import { AppShell } from "@/components/layout/AppShell"
import { CourseCard, JoinCourseCard } from "@/components/socratiq/CourseCard"
import { EmptyState } from "@/components/ui/States"
import { currentStudent, studentCourses } from "@/data/mockData"

export default function StudentCourses() {
  return (
    <AppShell
      role="student"
      userName={currentStudent.name}
      userEmail={currentStudent.email}
      courses={studentCourses}
      crumbs={[{ label: "Home", to: "/student" }, { label: "Courses" }]}
      search=""
    >
      <h1 className="text-xl font-semibold text-[var(--color-ink)]">All courses</h1>

      {studentCourses.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="No courses yet"
            description="Join a course with the code your instructor shared to see it here."
            action={{ label: "Join a course" }}
          />
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {studentCourses.map((c) => (
            <CourseCard key={c.id} course={c} to={`/student/courses/${c.id}`} />
          ))}
          <JoinCourseCard />
        </div>
      )}
    </AppShell>
  )
}
