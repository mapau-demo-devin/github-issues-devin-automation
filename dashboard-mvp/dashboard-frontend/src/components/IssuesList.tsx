import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, ExternalLink, User, Calendar } from 'lucide-react'

interface Issue {
  number: number
  title: string
  body: string
  state: string
  user: {
    login: string
    avatar_url: string
  }
  labels: Array<{
    name: string
    color: string
  }>
  created_at: string
  updated_at: string
  html_url: string
  comments: number
}

interface ApiResponse {
  issues: Issue[]
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function IssuesList() {
  const [owner, setOwner] = useState('microsoft')
  const [repo, setRepo] = useState('vscode')
  const [issues, setIssues] = useState<Issue[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<{ [key: string]: boolean }>({})

  const fetchIssues = async () => {
    if (!owner || !repo) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/repos/${owner}/${repo}/issues?limit=20`)
      if (!response.ok) {
        throw new Error(`Failed to fetch issues: ${response.statusText}`)
      }
      
      const data: ApiResponse = await response.json()
      setIssues(data.issues)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch issues')
    } finally {
      setLoading(false)
    }
  }

  const handleAction = async (issue: Issue, action: 'scope' | 'complete') => {
    const actionKey = `${issue.number}-${action}`
    setActionLoading(prev => ({ ...prev, [actionKey]: true }))
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/repos/${owner}/${repo}/issues/${issue.number}/${action}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      if (!response.ok) {
        throw new Error(`Failed to ${action} issue: ${response.statusText}`)
      }
      
      const result = await response.json()
      
      if (result.url) {
        window.open(result.url, '_blank')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} issue`)
    } finally {
      setActionLoading(prev => ({ ...prev, [actionKey]: false }))
    }
  }

  useEffect(() => {
    fetchIssues()
  }, [])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-4 items-end">
        <div className="flex-1">
          <Label htmlFor="owner">Repository Owner</Label>
          <Input
            id="owner"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            placeholder="e.g., microsoft"
          />
        </div>
        <div className="flex-1">
          <Label htmlFor="repo">Repository Name</Label>
          <Input
            id="repo"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="e.g., vscode"
          />
        </div>
        <Button onClick={fetchIssues} disabled={loading || !owner || !repo}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
          Load Issues
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {issues.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Issues from {owner}/{repo}</CardTitle>
            <CardDescription>
              Found {issues.length} issues
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">#</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Author</TableHead>
                  <TableHead>Labels</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {issues.map((issue) => (
                  <TableRow key={issue.number}>
                    <TableCell className="font-mono">
                      #{issue.number}
                    </TableCell>
                    <TableCell>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="link" className="p-0 h-auto text-left justify-start">
                            {issue.title}
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle className="flex items-center gap-2">
                              #{issue.number}: {issue.title}
                              <a
                                href={issue.html_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800"
                              >
                                <ExternalLink className="w-4 h-4" />
                              </a>
                            </DialogTitle>
                            <DialogDescription>
                              <div className="flex items-center gap-4 text-sm text-gray-600 mt-2">
                                <div className="flex items-center gap-1">
                                  <User className="w-4 h-4" />
                                  {issue.user.login}
                                </div>
                                <div className="flex items-center gap-1">
                                  <Calendar className="w-4 h-4" />
                                  Created {formatDate(issue.created_at)}
                                </div>
                                <Badge variant={issue.state === 'open' ? 'default' : 'secondary'}>
                                  {issue.state}
                                </Badge>
                              </div>
                            </DialogDescription>
                          </DialogHeader>
                          <div className="mt-4">
                            <div className="prose max-w-none">
                              <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded-md">
                                {issue.body || 'No description provided.'}
                              </pre>
                            </div>
                            <div className="flex gap-2 mt-6">
                              <Button
                                onClick={() => handleAction(issue, 'scope')}
                                disabled={actionLoading[`${issue.number}-scope`]}
                                variant="outline"
                              >
                                {actionLoading[`${issue.number}-scope`] ? (
                                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                ) : null}
                                Scope with Devin
                              </Button>
                              <Button
                                onClick={() => handleAction(issue, 'complete')}
                                disabled={actionLoading[`${issue.number}-complete`]}
                              >
                                {actionLoading[`${issue.number}-complete`] ? (
                                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                ) : null}
                                Complete with Devin
                              </Button>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <img
                          src={issue.user.avatar_url}
                          alt={issue.user.login}
                          className="w-6 h-6 rounded-full"
                        />
                        {issue.user.login}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {issue.labels.slice(0, 3).map((label) => (
                          <Badge
                            key={label.name}
                            variant="secondary"
                            style={{ backgroundColor: `#${label.color}20`, color: `#${label.color}` }}
                          >
                            {label.name}
                          </Badge>
                        ))}
                        {issue.labels.length > 3 && (
                          <Badge variant="secondary">
                            +{issue.labels.length - 3}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {formatDate(issue.updated_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleAction(issue, 'scope')}
                          disabled={actionLoading[`${issue.number}-scope`]}
                        >
                          {actionLoading[`${issue.number}-scope`] ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            'Scope'
                          )}
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleAction(issue, 'complete')}
                          disabled={actionLoading[`${issue.number}-complete`]}
                        >
                          {actionLoading[`${issue.number}-complete`] ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            'Complete'
                          )}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
