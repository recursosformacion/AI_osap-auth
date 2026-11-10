import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { authApi } from '../../api/authApi'
import type {
  EntityKind,
  EntityListItem,
  MembershipInfo,
  MembershipStatus,
} from '../../api/types'
import { useAuth } from '../../auth/AuthContext'

const KIND_LABELS: Record<EntityKind, string> = {
  coral: 'Coral',
  orquesta: 'Orquesta',
  grupo: 'Grupo',
}

const STATUS_LABELS: Record<MembershipStatus, string> = {
  pending: 'Pendiente de aprobación',
  approved: 'Aprobada',
  rejected: 'Rechazada',
}

function kindLabel(kind: EntityKind | undefined): string {
  return kind ? KIND_LABELS[kind] : '—'
}

// Ficha de entidades: solicitar pertenencia a una o varias entidades, dejar una
// pertenencia y crear/actualizar las entidades que el usuario gestiona.
export function EntityPage() {
  const { user, reload } = useAuth()
  const memberships: MembershipInfo[] = user?.memberships ?? []
  const managed = memberships.filter((membership) => membership.is_representative)
  const [entities, setEntities] = useState<EntityListItem[]>([])
  const [joinEntityId, setJoinEntityId] = useState('')
  const [managedEntityId, setManagedEntityId] = useState('')
  const [name, setName] = useState('')
  const [kind, setKind] = useState<EntityKind>('coral')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const joinable = entities.filter(
    (entity) =>
      !memberships.some(
        (membership) =>
          membership.entity_id === entity.id && membership.status !== 'rejected',
      ),
  )

  useEffect(() => {
    void (async () => {
      try {
        setEntities(await authApi.listEntities())
      } catch {
        setError('No se pudo cargar la lista de entidades.')
      }
    })()
  }, [])

  if (!user) return null

  const run = async (action: () => Promise<unknown>, success: string) => {
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      await action()
      await reload()
      setMessage(success)
    } catch {
      setError('No se pudo guardar el cambio de entidad.')
    } finally {
      setSaving(false)
    }
  }

  const selectManaged = (entityId: string) => {
    setManagedEntityId(entityId)
    const selected = managed.find((membership) => membership.entity_id === entityId)
    if (selected) {
      setName(selected.entity_name)
      setKind(selected.entity_kind)
    } else {
      setName('')
      setKind('coral')
    }
  }

  const join = () => {
    if (!joinEntityId) {
      setError('Elige una entidad de la lista.')
      return
    }
    void run(
      () => authApi.updateMyEntity({ action: 'join', entity_id: joinEntityId }),
      'Solicitud enviada. La entidad debe aprobarla para que seas miembro.',
    )
  }

  const leave = (membership: MembershipInfo) => {
    void run(
      () =>
        authApi.updateMyEntity({
          action: 'leave',
          entity_id: membership.entity_id,
        }),
      `Has dejado «${membership.entity_name}».`,
    )
  }

  const represent = () => {
    if (!name.trim()) {
      setError('Indica el nombre de la entidad que representas.')
      return
    }
    void run(
      () =>
        authApi.updateMyEntity({
          action: 'represent',
          entity_id: managedEntityId || undefined,
          entity_name: name.trim(),
          entity_kind: kind,
        }),
      managedEntityId
        ? 'Entidad actualizada.'
        : 'Entidad creada. Ya puedes ofrecerla a futuros usuarios.',
    )
  }

  return (
    <div>
      <section className="panel">
        <h3 className="panel-title">Mis entidades</h3>
        {memberships.length > 0 ? (
          <ul>
            {memberships.map((membership) => (
              <li key={membership.id}>
                <strong>{membership.entity_name}</strong> ({kindLabel(membership.entity_kind)}) —{' '}
                {STATUS_LABELS[membership.status]}
                {membership.is_representative ? ' · la representas' : ''}{' '}
                {membership.status !== 'rejected' ? (
                  <button
                    className="btn btn-danger btn-sm"
                    disabled={saving}
                    onClick={() => leave(membership)}
                  >
                    Dejar
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="panel-sub">No tienes ninguna pertenencia ni solicitud.</p>
        )}
        <p className="muted">
          Una solicitud no es una pertenencia hasta que el gestor de la entidad la aprueba.
        </p>
      </section>

      <section className="panel">
        <h3 className="panel-title">Solicitar pertenecer a una entidad</h3>
        <p className="panel-sub">
          Elige una entidad ya dada de alta. El gestor recibirá una notificación y decidirá de
          forma independiente para cada entidad.
        </p>
        <label htmlFor="entity-join" className="muted">Entidad</label>
        <select
          id="entity-join"
          value={joinEntityId}
          disabled={saving}
          onChange={(e) => setJoinEntityId(e.target.value)}
        >
          <option value="">— Ninguna —</option>
          {joinable.map((entity) => (
            <option key={entity.id} value={entity.id}>
              {entity.name} ({KIND_LABELS[entity.kind]})
            </option>
          ))}
        </select>
        <div className="row" style={{ marginTop: '0.75rem' }}>
          <button className="btn btn-primary btn-sm" disabled={saving || !joinEntityId} onClick={join}>
            Enviar solicitud
          </button>
        </div>
      </section>

      <section className="panel">
        <h3 className="panel-title">Representar una entidad</h3>
        <p className="panel-sub">
          Crea una entidad nueva o actualiza una que ya gestionas. Su nombre será el que se
          ofrezca a futuros usuarios para que soliciten unirse.
        </p>
        <label htmlFor="entity-managed" className="muted">Entidad que gestionas</label>
        <select
          id="entity-managed"
          value={managedEntityId}
          disabled={saving}
          onChange={(e) => selectManaged(e.target.value)}
        >
          <option value="">— Nueva entidad —</option>
          {managed.map((membership) => (
            <option key={membership.id} value={membership.entity_id}>
              {membership.entity_name}
            </option>
          ))}
        </select>
        <label htmlFor="entity-name" className="muted">Nombre de la entidad</label>
        <input
          id="entity-name"
          value={name}
          disabled={saving}
          maxLength={120}
          placeholder="Coral nnnnn / Orquesta kkkkk / Grup sss"
          onChange={(e) => setName(e.target.value)}
        />
        <label htmlFor="entity-kind" className="muted">Tipo de entidad</label>
        <select
          id="entity-kind"
          value={kind}
          disabled={saving}
          onChange={(e) => setKind(e.target.value as EntityKind)}
        >
          {Object.entries(KIND_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <div className="row" style={{ marginTop: '0.75rem' }}>
          <button className="btn btn-primary btn-sm" disabled={saving} onClick={represent}>
            {managedEntityId ? 'Actualizar entidad' : 'Crear entidad'}
          </button>
        </div>
      </section>

      {error && <p className="error">{error}</p>}
      {message && <p className="muted">{message}</p>}

      <Link className="btn btn-outline btn-sm" to="/auth/account">
        Volver a tu cuenta
      </Link>
    </div>
  )
}
