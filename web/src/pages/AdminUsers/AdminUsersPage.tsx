import { useEffect, useMemo, useState, type ReactNode } from 'react'

import { authApi } from '../../api/authApi'
import type { UserMe } from '../../api/types'
import { ErrorMessage } from '../../components/ErrorMessage'
import { FormField } from '../../components/FormField'
import { Loading } from '../../components/Loading'
import { PasswordField } from '../../components/PasswordField'
import { useSubmission } from '../../hooks/useSubmission'

const ALL_ROLES = ['user', 'moderator', 'admin']
const STATUSES = ['active', 'pending_verification', 'disabled']

function formatDate(value: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })
}

interface Editor {
  user?: UserMe
  email?: string
  name: string
  password: string
  roles: string[]
  status: string
}

const emptyEditor: Editor = { name: '', password: '', roles: ['user'], status: 'active' }

export function AdminUsersPage() {
  const [users, setUsers] = useState<UserMe[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [filterVerified, setFilterVerified] = useState<'all' | 'verified' | 'pending'>('all')
  const [editor, setEditor] = useState<Editor | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const load = async () => {
    try {
      setUsers(await authApi.adminListUsers())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar usuarios')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const filtered = useMemo(() => {
    if (!users) return []
    const q = query.trim().toLowerCase()
    return users.filter((u) => {
      const matchesQuery = !q || u.email.toLowerCase().includes(q) || (u.name ?? '').toLowerCase().includes(q)
      const matchesVerified =
        filterVerified === 'all' ||
        (filterVerified === 'verified' && u.email_verified) ||
        (filterVerified === 'pending' && !u.email_verified)
      return matchesQuery && matchesVerified
    })
  }, [users, query, filterVerified])

  const openCreate = () => setEditor({ ...emptyEditor })
  const openEdit = (u: UserMe) =>
    setEditor({ user: u, name: u.name ?? '', password: '', roles: [...u.roles], status: u.status })

  const save = useSubmission(async () => {
    if (!editor) return
    if (editor.user) {
      const updated = await authApi.adminUpdateUser(editor.user.user_id, {
        name: editor.name,
        roles: editor.roles,
        status: editor.status,
      })
      setUsers((prev) =>
        prev ? prev.map((u) => (u.user_id === updated.user_id ? updated : u)) : prev,
      )
    } else {
      const created = await authApi.adminCreateUser({
        email: editor.email ?? '',
        password: editor.password,
        name: editor.name || undefined,
        roles: editor.roles,
      })
      setUsers((prev) => (prev ? [created, ...prev] : [created]))
    }
    setEditor(null)
  })

  const doDelete = useSubmission(async () => {
    if (!deleteId) return
    await authApi.adminDeleteUser(deleteId)
    setUsers((prev) => (prev ? prev.filter((u) => u.user_id !== deleteId) : prev))
    setDeleteId(null)
  })

  if (error) return <ErrorMessage message={error} />
  if (!users) return <Loading label="Cargando usuarios…" />

  return (
    <div>
      <div className="row" style={{ marginBottom: 16, justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>Administración de usuarios</h2>
        <button className="btn btn-primary btn-sm" onClick={openCreate}>
          + Nuevo usuario
        </button>
      </div>

      <div className="row" style={{ marginBottom: 16 }}>
        <input
          className="form-input"
          style={{ maxWidth: 280 }}
          placeholder="Buscar por email o nombre…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="form-input"
          style={{ maxWidth: 200 }}
          value={filterVerified}
          onChange={(e) => setFilterVerified(e.target.value as typeof filterVerified)}
        >
          <option value="all">Todos</option>
          <option value="verified">Verificados</option>
          <option value="pending">Sin verificar</option>
        </select>
      </div>

      <div className="panel">
        <table className="table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Nombre</th>
              <th>Email verificado</th>
              <th>Estado</th>
              <th>Roles</th>
              <th>Alta</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u) => (
              <tr key={u.user_id}>
                <td>{u.email}</td>
                <td>{u.name || '—'}</td>
                <td>
                  {u.email_verified ? (
                    <span className="badge badge-ok">Sí</span>
                  ) : (
                    <span className="badge badge-warn">No</span>
                  )}
                </td>
                <td>
                  <StatusBadge status={u.status} />
                </td>
                <td>{u.roles.join(', ')}</td>
                <td>{formatDate(u.created_at)}</td>
                <td>
                  <div className="row" style={{ gap: 6 }}>
                    <button className="btn btn-outline btn-sm" onClick={() => openEdit(u)}>
                      Editar
                    </button>
                    <button className="btn btn-danger btn-sm" onClick={() => setDeleteId(u.user_id)}>
                      Eliminar
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted">
                  Sin resultados.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {editor ? (
        <EditorModal
          editor={editor}
          onChange={setEditor}
          saving={save.submitting}
          error={save.error}
          onSave={() => void save.run()}
          onClose={() => setEditor(null)}
        />
      ) : null}

      {deleteId ? (
        <ConfirmDelete
          saving={doDelete.submitting}
          error={doDelete.error}
          onConfirm={() => void doDelete.run()}
          onClose={() => setDeleteId(null)}
        />
      ) : null}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'active') return <span className="badge badge-ok">Activo</span>
  if (status === 'pending_verification') return <span className="badge badge-warn">Sin verificar</span>
  if (status === 'disabled') return <span className="badge badge-danger">Deshabilitado</span>
  return <span className="badge badge-danger">Eliminado</span>
}

function Modal({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15,23,42,0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
        zIndex: 50,
      }}
    >
      <div className="panel" style={{ width: '100%', maxWidth: 480, marginBottom: 0 }}>
        <h3 className="panel-title">{title}</h3>
        {children}
      </div>
    </div>
  )
}

function EditorModal({
  editor,
  onChange,
  saving,
  error,
  onSave,
  onClose,
}: {
  editor: Editor
  onChange: (e: Editor) => void
  saving: boolean
  error: string | null
  onSave: () => void
  onClose: () => void
}) {
  const set = (patch: Partial<Editor>) => onChange({ ...editor, ...patch })
  return (
    <Modal title={editor.user ? 'Editar usuario' : 'Nuevo usuario'}>
      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          onSave()
        }}
      >
        {!editor.user ? (
          <FormField label="Email" name="email" type="email" value={editor.email ?? ''} onChange={(v) => set({ email: v })} required />
        ) : null}
        <FormField label="Nombre" name="name" value={editor.name} onChange={(v) => set({ name: v })} />
        {!editor.user ? (
          <PasswordField label="Contraseña" name="password" value={editor.password} onChange={(v) => set({ password: v })} />
        ) : null}
        <div className="form-field">
          <label>Roles</label>
          <div className="row">
            {ALL_ROLES.map((r) => (
              <label key={r} style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <input
                  type="checkbox"
                  checked={editor.roles.includes(r)}
                  onChange={(e) =>
                    set({
                      roles: e.target.checked
                        ? [...editor.roles, r]
                        : editor.roles.filter((x) => x !== r),
                    })
                  }
                />
                {r}
              </label>
            ))}
          </div>
        </div>
        {editor.user ? (
          <div className="form-field">
            <label>Estado</label>
            <select className="form-input" value={editor.status} onChange={(e) => set({ status: e.target.value })}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        <ErrorMessage message={error} />
        <div className="row" style={{ marginTop: 16 }}>
          <button className="btn btn-primary" type="submit" disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar'}
          </button>
          <button className="btn btn-outline" type="button" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  )
}

function ConfirmDelete({
  saving,
  error,
  onConfirm,
  onClose,
}: {
  saving: boolean
  error: string | null
  onConfirm: () => void
  onClose: () => void
}) {
  return (
    <Modal title="Eliminar usuario">
      <div className="alert alert-error" role="alert">
        Esta acción elimina el usuario definitivamente (se revocan sus sesiones y se conserva
        solo el dato agregado en los servicios). No puede deshacerse.
      </div>
      <ErrorMessage message={error} />
      <div className="row" style={{ marginTop: 8 }}>
        <button className="btn btn-danger" onClick={onConfirm} disabled={saving}>
          {saving ? 'Eliminando…' : 'Eliminar definitivamente'}
        </button>
        <button className="btn btn-outline" onClick={onClose}>
          Cancelar
        </button>
      </div>
    </Modal>
  )
}
