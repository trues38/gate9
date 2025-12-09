import { Suspense } from "react"
import DashboardMain from "../../components/DashboardMain"

export const dynamic = 'force-dynamic'

export default function DashboardPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <DashboardMain />
        </Suspense>
    )
}
