export function Badge({
  children,
  tone = 'pending',
}: {
  children: React.ReactNode
  tone?: 'pending' | 'success' | 'error'
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}
