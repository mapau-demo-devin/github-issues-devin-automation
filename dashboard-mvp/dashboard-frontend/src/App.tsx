import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import IssuesList from './components/IssuesList'
import SessionsList from './components/SessionsList'
import './App.css'

function App() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            GitHub Issues Devin Automation Dashboard
          </h1>
          <p className="text-gray-600">
            Manage GitHub issues with AI-powered scoping and completion
          </p>
        </div>

        <Tabs defaultValue="issues" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="issues">Issues</TabsTrigger>
            <TabsTrigger value="sessions">Sessions</TabsTrigger>
          </TabsList>
          
          <TabsContent value="issues" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>GitHub Issues</CardTitle>
                <CardDescription>
                  Browse and manage GitHub issues from your repositories
                </CardDescription>
              </CardHeader>
              <CardContent>
                <IssuesList />
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="sessions" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Devin Sessions</CardTitle>
                <CardDescription>
                  View and manage your active Devin AI sessions
                </CardDescription>
              </CardHeader>
              <CardContent>
                <SessionsList />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default App
