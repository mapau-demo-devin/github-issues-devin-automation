import { useState } from 'react'
import './App.css'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2, ExternalLink, Github } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Issue {
  number: number
  title: string
  state: string
  html_url: string
  labels: { name: string; color: string }[]
  created_at: string
}

interface ScopeResult {
  confidence_level: string
  brief_analysis: string
  session_id: string
  session_url: string
}

interface CompleteResult {
  session_id: string
  session_url: string
}

function App() {
  const [listRepo, setListRepo] = useState('mapau-demo-devin/running-buddy')
  const [listState, setListState] = useState('open')
  const [listLimit, setListLimit] = useState('10')
  const [issues, setIssues] = useState<Issue[]>([])
  const [listLoading, setListLoading] = useState(false)
  const [listError, setListError] = useState('')

  const [scopeRepo, setScopeRepo] = useState('mapau-demo-devin/running-buddy')
  const [scopeIssueNumber, setScopeIssueNumber] = useState('')
  const [scopeResult, setScopeResult] = useState<ScopeResult | null>(null)
  const [scopeLoading, setScopeLoading] = useState(false)
  const [scopeError, setScopeError] = useState('')

  const [completeRepo, setCompleteRepo] = useState('mapau-demo-devin/running-buddy')
  const [completeIssueNumber, setCompleteIssueNumber] = useState('')
  const [completeResult, setCompleteResult] = useState<CompleteResult | null>(null)
  const [completeLoading, setCompleteLoading] = useState(false)
  const [completeError, setCompleteError] = useState('')

  const handleListIssues = async () => {
    setListLoading(true)
    setListError('')
    setIssues([])
    
    try {
      const [owner, repo] = listRepo.split('/')
      if (!owner || !repo) {
        throw new Error('Invalid repo format. Use owner/repo')
      }
      
      const response = await fetch(
        `${API_URL}/api/repos/${owner}/${repo}/issues?state=${listState}&limit=${listLimit}`
      )
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to fetch issues')
      }
      
      const data = await response.json()
      setIssues(data.issues || [])
    } catch (error) {
      setListError(error instanceof Error ? error.message : 'An error occurred')
    } finally {
      setListLoading(false)
    }
  }

  const handleScopeIssue = async () => {
    setScopeLoading(true)
    setScopeError('')
    setScopeResult(null)
    
    try {
      const [owner, repo] = scopeRepo.split('/')
      if (!owner || !repo) {
        throw new Error('Invalid repo format. Use owner/repo')
      }
      
      if (!scopeIssueNumber) {
        throw new Error('Issue number is required')
      }
      
      const response = await fetch(
        `${API_URL}/api/repos/${owner}/${repo}/issues/${scopeIssueNumber}/scope`,
        { method: 'POST' }
      )
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to scope issue')
      }
      
      const data = await response.json()
      setScopeResult(data)
    } catch (error) {
      setScopeError(error instanceof Error ? error.message : 'An error occurred')
    } finally {
      setScopeLoading(false)
    }
  }

  const handleCompleteIssue = async () => {
    setCompleteLoading(true)
    setCompleteError('')
    setCompleteResult(null)
    
    try {
      const [owner, repo] = completeRepo.split('/')
      if (!owner || !repo) {
        throw new Error('Invalid repo format. Use owner/repo')
      }
      
      if (!completeIssueNumber) {
        throw new Error('Issue number is required')
      }
      
      const response = await fetch(
        `${API_URL}/api/repos/${owner}/${repo}/issues/${completeIssueNumber}/complete`,
        { method: 'POST' }
      )
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to complete issue')
      }
      
      const data = await response.json()
      setCompleteResult(data)
    } catch (error) {
      setCompleteError(error instanceof Error ? error.message : 'An error occurred')
    } finally {
      setCompleteLoading(false)
    }
  }

  return (
    <div className="container mx-auto py-8 max-w-6xl">
      <div className="mb-8 text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Github className="w-8 h-8" />
          <h1 className="text-4xl font-bold">GitHub Issues Devin Automation</h1>
        </div>
        <p className="text-muted-foreground">
          Manage GitHub issues with AI-powered automation using Devin
        </p>
      </div>

      <Tabs defaultValue="list" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="list">List Issues</TabsTrigger>
          <TabsTrigger value="scope">Scope Issue</TabsTrigger>
          <TabsTrigger value="complete">Complete Issue</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <Card>
            <CardHeader>
              <CardTitle>List GitHub Issues</CardTitle>
              <CardDescription>
                Fetch and view issues from any GitHub repository
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="list-repo">Repository (owner/repo)</Label>
                  <Input
                    id="list-repo"
                    placeholder="owner/repo"
                    value={listRepo}
                    onChange={(e) => setListRepo(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="list-state">State</Label>
                  <Select value={listState} onValueChange={setListState}>
                    <SelectTrigger id="list-state">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">Open</SelectItem>
                      <SelectItem value="closed">Closed</SelectItem>
                      <SelectItem value="all">All</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="list-limit">Limit</Label>
                  <Input
                    id="list-limit"
                    type="number"
                    min="1"
                    max="100"
                    value={listLimit}
                    onChange={(e) => setListLimit(e.target.value)}
                  />
                </div>
              </div>
              
              <Button 
                onClick={handleListIssues} 
                disabled={listLoading}
                className="w-full"
              >
                {listLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Fetching Issues...
                  </>
                ) : (
                  'Fetch Issues'
                )}
              </Button>

              {listError && (
                <Alert variant="destructive">
                  <AlertDescription>{listError}</AlertDescription>
                </Alert>
              )}

              {issues.length > 0 && (
                <div className="border rounded-lg">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-20">#</TableHead>
                        <TableHead>Title</TableHead>
                        <TableHead className="w-24">State</TableHead>
                        <TableHead className="w-32">Labels</TableHead>
                        <TableHead className="w-20">Link</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {issues.map((issue) => (
                        <TableRow key={issue.number}>
                          <TableCell className="font-medium">#{issue.number}</TableCell>
                          <TableCell>{issue.title}</TableCell>
                          <TableCell>
                            <Badge variant={issue.state === 'open' ? 'default' : 'secondary'}>
                              {issue.state}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {issue.labels.slice(0, 2).map((label) => (
                                <Badge 
                                  key={label.name} 
                                  variant="outline"
                                  className="text-xs"
                                >
                                  {label.name}
                                </Badge>
                              ))}
                            </div>
                          </TableCell>
                          <TableCell>
                            <a 
                              href={issue.html_url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="inline-flex items-center text-blue-600 hover:text-blue-800"
                            >
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="scope">
          <Card>
            <CardHeader>
              <CardTitle>Scope Issue with Devin AI</CardTitle>
              <CardDescription>
                Analyze an issue and get a confidence score and scoping analysis from Devin
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="scope-repo">Repository (owner/repo)</Label>
                  <Input
                    id="scope-repo"
                    placeholder="owner/repo"
                    value={scopeRepo}
                    onChange={(e) => setScopeRepo(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="scope-issue">Issue Number</Label>
                  <Input
                    id="scope-issue"
                    type="number"
                    placeholder="e.g., 123"
                    value={scopeIssueNumber}
                    onChange={(e) => setScopeIssueNumber(e.target.value)}
                  />
                </div>
              </div>
              
              <Button 
                onClick={handleScopeIssue} 
                disabled={scopeLoading}
                className="w-full"
              >
                {scopeLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Scoping Issue...
                  </>
                ) : (
                  'Scope Issue'
                )}
              </Button>

              {scopeError && (
                <Alert variant="destructive">
                  <AlertDescription>{scopeError}</AlertDescription>
                </Alert>
              )}

              {scopeResult && (
                <div className="space-y-4">
                  <Alert>
                    <AlertDescription>
                      <div className="space-y-3">
                        <div>
                          <span className="font-semibold">Confidence Level: </span>
                          <Badge 
                            variant={
                              scopeResult.confidence_level === 'High' 
                                ? 'default' 
                                : scopeResult.confidence_level === 'Medium'
                                ? 'secondary'
                                : 'outline'
                            }
                          >
                            {scopeResult.confidence_level}
                          </Badge>
                        </div>
                        <div>
                          <span className="font-semibold">Analysis: </span>
                          <p className="mt-1 text-sm">{scopeResult.brief_analysis}</p>
                        </div>
                        <div>
                          <span className="font-semibold">Devin Session: </span>
                          <a 
                            href={scopeResult.session_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 underline"
                          >
                            View Session <ExternalLink className="h-3 w-3" />
                          </a>
                        </div>
                      </div>
                    </AlertDescription>
                  </Alert>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="complete">
          <Card>
            <CardHeader>
              <CardTitle>Complete Issue with Devin AI</CardTitle>
              <CardDescription>
                Create a Devin session to implement and complete an issue
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="complete-repo">Repository (owner/repo)</Label>
                  <Input
                    id="complete-repo"
                    placeholder="owner/repo"
                    value={completeRepo}
                    onChange={(e) => setCompleteRepo(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="complete-issue">Issue Number</Label>
                  <Input
                    id="complete-issue"
                    type="number"
                    placeholder="e.g., 123"
                    value={completeIssueNumber}
                    onChange={(e) => setCompleteIssueNumber(e.target.value)}
                  />
                </div>
              </div>
              
              <Button 
                onClick={handleCompleteIssue} 
                disabled={completeLoading}
                className="w-full"
              >
                {completeLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating Devin Session...
                  </>
                ) : (
                  'Complete Issue'
                )}
              </Button>

              {completeError && (
                <Alert variant="destructive">
                  <AlertDescription>{completeError}</AlertDescription>
                </Alert>
              )}

              {completeResult && (
                <Alert>
                  <AlertDescription>
                    <div className="space-y-3">
                      <div>
                        <span className="font-semibold">Session Created Successfully!</span>
                      </div>
                      <div>
                        <span className="font-semibold">Devin Session: </span>
                        <a 
                          href={completeResult.session_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 underline"
                        >
                          View Session <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Devin will now work on implementing this issue. You can track progress in the session.
                      </div>
                    </div>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default App
