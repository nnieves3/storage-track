import {
  ArrowLeftRight,
  Check,
  CircleHelp,
  DoorOpen,
  LayoutGrid,
  LoaderCircle,
  MapPin,
  Package,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

type SubLocation = {
  id: number | null;
  name: string;
  location_id: number | null;
};

type Location = {
  id: number | null;
  name: string;
  sub_locations: SubLocation[];
};

type Item = {
  id: number | null;
  name: string;
  description: string;
  count: number;
  location: Location | null;
  sub_location: SubLocation | null;
  checked_out: boolean;
  created_at: string | null;
  updated_at: string | null;
};

type DialogState =
  | { kind: "location" }
  | { kind: "item"; location: Location }
  | { kind: "move"; item: Item }
  | { kind: "delete-item"; item: Item }
  | { kind: "delete-location"; location: Location }
  | null;

const ADD_NEW_SUB_LOCATION = "__add_new__";

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { error?: string }
      | null;
    throw new Error(body?.error ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function itemMatches(item: Item, query: string): boolean {
  const search = query.trim().toLocaleLowerCase();
  return (
    !search ||
    item.name.toLocaleLowerCase().includes(search) ||
    item.description.toLocaleLowerCase().includes(search)
  );
}

function App() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [serviceConnected, setServiceConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [query, setQuery] = useState("");
  const [dialog, setDialog] = useState<DialogState>(null);

  const refresh = useCallback(async () => {
    const [nextLocations, nextItems] = await Promise.all([
      api<Location[]>("/locations"),
      api<Item[]>("/items"),
    ]);
    setLocations(nextLocations);
    setItems(nextItems);
    setServiceConnected(true);
  }, []);

  useEffect(() => {
    void refresh()
      .catch((cause: unknown) => {
        setServiceConnected(false);
        setError(
          cause instanceof Error ? cause.message : "Could not load inventory.",
        );
      })
      .finally(() => setLoading(false));
  }, [refresh]);

  const filteredItems = useMemo(
    () => items.filter((item) => itemMatches(item, query)),
    [items, query],
  );
  const checkedOutCount = items.filter((item) => item.checked_out).length;
  const unitCount = items.reduce((total, item) => total + item.count, 0);

  const perform = async (action: () => Promise<void>, successMessage: string) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      await refresh();
      setDialog(null);
      setNotice(successMessage);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The action failed.");
    } finally {
      setBusy(false);
    }
  };

  const createSubLocation = async (
    locationId: number,
    name: string,
  ): Promise<SubLocation> => {
    setBusy(true);
    try {
      const subLocation = await api<SubLocation>(
        `/locations/${locationId}/sub-locations`,
        {
          method: "POST",
          body: JSON.stringify({ name }),
        },
      );
      setLocations((current) =>
        current.map((location) =>
          location.id === locationId
            ? {
                ...location,
                sub_locations: [...location.sub_locations, subLocation],
              }
            : location,
        ),
      );
      return subLocation;
    } finally {
      setBusy(false);
    }
  };

  const submitDialog = async (form: FormData) => {
    if (!dialog) return;
    if (dialog.kind === "location") {
      const name = String(form.get("name") ?? "").trim();
      await perform(
        async () => {
          await api("/locations", {
            method: "POST",
            body: JSON.stringify({ name }),
          });
        },
        `${name} was added.`,
      );
      return;
    }
    if (dialog.kind === "item") {
      const name = String(form.get("name") ?? "").trim();
      const subLocationId = String(form.get("sub_location_id") ?? "");
      await perform(
        async () => {
          await api("/items", {
            method: "POST",
            body: JSON.stringify({
              name,
              description: String(form.get("description") ?? "").trim(),
              count: Number(form.get("count")),
              location_id: dialog.location.id,
              ...(subLocationId ? { sub_location_id: Number(subLocationId) } : {}),
            }),
          });
        },
        `${name} was added to ${dialog.location.name}.`,
      );
      return;
    }
    if (dialog.kind === "move" && dialog.item.id !== null) {
      const locationId = Number(form.get("location_id"));
      const subLocationId = String(form.get("sub_location_id") ?? "");
      const target = locations.find((location) => location.id === locationId);
      await perform(
        async () => {
          await api(`/items/${dialog.item.id}/move`, {
            method: "PATCH",
            body: JSON.stringify({
              location_id: locationId,
              ...(subLocationId ? { sub_location_id: Number(subLocationId) } : {}),
            }),
          });
        },
        `${dialog.item.name} moved to ${target?.name ?? "the new location"}.`,
      );
    }
  };

  const toggleCheckout = (item: Item) => {
    if (item.id === null) return;
    void perform(
      async () => {
        await api(`/items/${item.id}/${item.checked_out ? "checkin" : "checkout"}`, {
          method: "POST",
        });
      },
      item.checked_out ? `${item.name} was checked in.` : `${item.name} checked out.`,
    );
  };

  const deleteItem = (item: Item) => {
    if (item.id === null) return;
    void perform(
      async () => {
        await api(`/items/${item.id}?count=0`, { method: "DELETE" });
      },
      `${item.name} was deleted.`,
    );
  };

  const deleteLocation = (location: Location) => {
    if (location.id === null) return;
    const locationItems = items.filter(
      (item) => item.location?.id === location.id,
    );
    const cascade = locationItems.length > 0;
    void perform(
      async () => {
        await api(
          `/locations/${location.id}${cascade ? "?cascade=true" : ""}`,
          { method: "DELETE" },
        );
      },
      cascade
        ? `${location.name} and ${locationItems.length} item${locationItems.length === 1 ? "" : "s"} were deleted.`
        : `${location.name} was deleted.`,
    );
  };

  const unassignedItems = filteredItems.filter((item) => item.location === null);

  if (loading) {
    return (
      <main className="loading-screen">
        <LoaderCircle className="spin" size={28} />
        <span>Loading your inventory…</span>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Storage Track home">
          <span className="brand-mark">
            <Package size={20} strokeWidth={2.2} />
          </span>
          <span>storage<span className="brand-light">track</span></span>
        </a>
        <div className="topbar-right">
          <span className={`connection-indicator${serviceConnected ? "" : " offline"}`}>
            <i /> {serviceConnected ? "Service connected" : "Service unavailable"}
          </span>
          <button className="button button-primary" onClick={() => setDialog({ kind: "location" })}>
            <Plus size={17} /> Add location
          </button>
        </div>
      </header>

      <section className="page-heading">
        <div>
          <div className="eyebrow"><LayoutGrid size={14} /> YOUR INVENTORY</div>
          <h1>Everything in its place.</h1>
          <p className="subtitle">A clear view of what you have and where it lives.</p>
        </div>
        <label className="search-box">
          <Search size={17} />
          <input
            aria-label="Search inventory"
            placeholder="Search items…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          {query && (
            <button aria-label="Clear search" className="icon-button" onClick={() => setQuery("")}>
              <X size={15} />
            </button>
          )}
        </label>
      </section>

      <section className="stats-grid" aria-label="Inventory summary">
        <Stat icon={<MapPin size={17} />} label="Locations" value={locations.length} />
        <Stat icon={<Package size={17} />} label="Items in inventory" value={unitCount} />
        <Stat icon={<DoorOpen size={17} />} label="Checked out" value={checkedOutCount} />
      </section>

      {error && (
        <div className="alert alert-error" role="alert">
          <CircleHelp size={17} /> <span>{error}</span>
          <button className="icon-button" aria-label="Dismiss error" onClick={() => setError("")}><X size={16} /></button>
        </div>
      )}
      {notice && (
        <div className="alert alert-success" role="status">
          <Check size={17} /> <span>{notice}</span>
          <button className="icon-button" aria-label="Dismiss message" onClick={() => setNotice("")}><X size={16} /></button>
        </div>
      )}

      <section className="locations-section">
        <div className="section-heading">
          <div>
            <h2>Locations <span className="count-pill">{locations.length}</span></h2>
            <p>Browse your items by where they’re stored.</p>
          </div>
          <span className="section-hint"><MapPin size={15} /> {unitCount} total units</span>
        </div>

        {locations.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon"><MapPin size={23} /></span>
            <h3>No locations yet</h3>
            <p>Create your first location to start organizing your inventory.</p>
            <button className="button button-primary" onClick={() => setDialog({ kind: "location" })}>
              <Plus size={17} /> Add your first location
            </button>
          </div>
        ) : (
          <div className="location-list">
            {locations.map((location) => {
              const locationItems = filteredItems.filter(
                (item) => item.location?.id === location.id,
              );
              const locationUnitCount = locationItems.reduce(
                (total, item) => total + item.count,
                0,
              );
              return (
                <LocationCard
                  key={location.id ?? location.name}
                  location={location}
                  items={locationItems}
                  unitCount={locationUnitCount}
                  busy={busy}
                  onAddItem={() => setDialog({ kind: "item", location })}
                  onDeleteLocation={() => setDialog({ kind: "delete-location", location })}
                  onMove={(item) => setDialog({ kind: "move", item })}
                  onToggleCheckout={toggleCheckout}
                  onDeleteItem={(item) => setDialog({ kind: "delete-item", item })}
                />
              );
            })}
          </div>
        )}

        {unassignedItems.length > 0 && (
          <LocationCard
            location={{ id: null, name: "Unassigned items", sub_locations: [] }}
            items={unassignedItems}
            unitCount={unassignedItems.reduce((total, item) => total + item.count, 0)}
            busy={busy}
            onAddItem={() => undefined}
            onDeleteLocation={() => undefined}
            onMove={(item) => setDialog({ kind: "move", item })}
            onToggleCheckout={toggleCheckout}
            onDeleteItem={(item) => setDialog({ kind: "delete-item", item })}
            unassigned
          />
        )}
      </section>

      {dialog && (
        <ActionDialog
          key={dialog.kind === "item" ? `${dialog.kind}-${dialog.location.id}` : dialog.kind}
          dialog={dialog}
          locations={locations}
          items={items}
          busy={busy}
          error={error}
          onCreateSubLocation={createSubLocation}
          onClose={() => setDialog(null)}
          onSubmit={submitDialog}
          onDeleteItem={deleteItem}
          onDeleteLocation={deleteLocation}
        />
      )}
    </main>
  );
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="stat-card">
      <span className="stat-icon">{icon}</span>
      <div>
        <div className="stat-value">{value.toLocaleString()}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

function LocationCard({
  location,
  items,
  unitCount,
  busy,
  onAddItem,
  onDeleteLocation,
  onMove,
  onToggleCheckout,
  onDeleteItem,
  unassigned = false,
}: {
  location: Location;
  items: Item[];
  unitCount: number;
  busy: boolean;
  onAddItem: () => void;
  onDeleteLocation: () => void;
  onMove: (item: Item) => void;
  onToggleCheckout: (item: Item) => void;
  onDeleteItem: (item: Item) => void;
  unassigned?: boolean;
}) {
  return (
    <article className={`location-card${unassigned ? " unassigned-card" : ""}`}>
      <div className="location-card-heading">
        <div className="location-title-wrap">
          <span className="location-icon"><MapPin size={18} /></span>
          <div>
            <h3>{location.name}</h3>
            <div className="location-meta">
              {unassigned
                ? "Items without a location"
                : `${location.sub_locations.length} sub-location${location.sub_locations.length === 1 ? "" : "s"}`}
              <span className="meta-dot" />
              {unitCount} unit{unitCount === 1 ? "" : "s"}
            </div>
          </div>
        </div>
        <div className="location-actions">
          {!unassigned && (
            <>
              <button className="button button-outline" onClick={onAddItem} disabled={busy}>
                <Plus size={16} /> Add item
              </button>
              <button
                className="icon-button danger-hover"
                aria-label={`Delete ${location.name}`}
                title="Delete location"
                onClick={onDeleteLocation}
                disabled={busy}
              >
                <Trash2 size={16} />
              </button>
            </>
          )}
        </div>
      </div>

      {location.sub_locations.length > 0 && !unassigned && (
        <div className="shelf-list">
          {location.sub_locations.map((subLocation) => (
            <span className="shelf-chip" key={subLocation.id ?? subLocation.name}>
              {subLocation.name}
            </span>
          ))}
        </div>
      )}

      <div className="table-scroll">
        <table className="inventory-table">
          <thead>
            <tr>
              <th>ITEM</th>
              <th>SUB-LOCATION</th>
              <th>QUANTITY</th>
              <th>STATUS</th>
              <th><span className="visually-hidden">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={5} className="table-empty">
                  {unassigned ? "No unassigned items." : "Nothing stored here yet."}
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id ?? item.name}>
                  <td>
                    <div className="item-name">{item.name}</div>
                    {item.description && <div className="item-description">{item.description}</div>}
                  </td>
                  <td>
                    {item.sub_location ? (
                      <span className="sublocation-label">{item.sub_location.name}</span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td><span className="quantity">{item.count}</span></td>
                  <td>
                    <span className={`status-pill${item.checked_out ? " status-out" : ""}`}>
                      <i /> {item.checked_out ? "Checked out" : "Available"}
                    </span>
                  </td>
                  <td>
                    <div className="row-actions">
                      <button className="row-action" title="Move item" onClick={() => onMove(item)} disabled={busy}>
                        <ArrowLeftRight size={15} /><span>Move</span>
                      </button>
                      <button
                        className={`row-action${item.checked_out ? " checked-in-action" : ""}`}
                        title={item.checked_out ? "Check item in" : "Check item out"}
                        onClick={() => onToggleCheckout(item)}
                        disabled={busy}
                      >
                        <DoorOpen size={15} /><span>{item.checked_out ? "Check in" : "Check out"}</span>
                      </button>
                      <button
                        className="row-action row-delete"
                        title="Delete item"
                        onClick={() => onDeleteItem(item)}
                        disabled={busy}
                      >
                        <Trash2 size={15} /><span>Delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function ActionDialog({
  dialog,
  locations,
  items,
  busy,
  error,
  onCreateSubLocation,
  onClose,
  onSubmit,
  onDeleteItem,
  onDeleteLocation,
}: {
  dialog: Exclude<DialogState, null>;
  locations: Location[];
  items: Item[];
  busy: boolean;
  error: string;
  onCreateSubLocation: (
    locationId: number,
    name: string,
  ) => Promise<SubLocation>;
  onClose: () => void;
  onSubmit: (form: FormData) => Promise<void>;
  onDeleteItem: (item: Item) => void;
  onDeleteLocation: (location: Location) => void;
}) {
  const initialLocationId =
    dialog.kind === "move"
      ? dialog.item.location?.id ?? locations[0]?.id ?? null
      : dialog.kind === "item"
        ? dialog.location.id
        : null;
  const [selectedLocationId, setSelectedLocationId] = useState<number | null>(
    initialLocationId,
  );
  const selectedLocation = locations.find(
    (location) => location.id === selectedLocationId,
  );
  const subLocations = selectedLocation?.sub_locations ?? [];
  const defaultSubLocation =
    dialog.kind === "move" && dialog.item.location?.id === selectedLocationId
      ? dialog.item.sub_location?.id
      : subLocations.find((subLocation) => subLocation.name === "Other")?.id;
  const initialSubLocationId =
    dialog.kind === "item" ? String(defaultSubLocation ?? "") : "";
  const [selectedSubLocationId, setSelectedSubLocationId] =
    useState(initialSubLocationId);
  const [subLocationBeforeAdd, setSubLocationBeforeAdd] =
    useState(initialSubLocationId);
  const [creatingSubLocation, setCreatingSubLocation] = useState(false);
  const [newSubLocationName, setNewSubLocationName] = useState("");
  const [subLocationError, setSubLocationError] = useState("");
  const actionItem =
    dialog.kind === "delete-item" || dialog.kind === "move" ? dialog.item : null;
  const deleteLocationItemCount =
    dialog.kind === "delete-location"
      ? items.filter((item) => item.location?.id === dialog.location.id).length
      : 0;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void onSubmit(new FormData(event.currentTarget));
  };

  const addSubLocation = async () => {
    if (dialog.kind !== "item" || dialog.location.id === null) return;
    const name = newSubLocationName.trim();
    if (!name) return;
    setSubLocationError("");
    try {
      const subLocation = await onCreateSubLocation(dialog.location.id, name);
      if (subLocation.id === null) {
        throw new Error("The new sub-location was created without an ID.");
      }
      const id = String(subLocation.id);
      setSelectedSubLocationId(id);
      setSubLocationBeforeAdd(id);
      setNewSubLocationName("");
      setCreatingSubLocation(false);
    } catch (cause) {
      setSubLocationError(
        cause instanceof Error ? cause.message : "Could not create sub-location.",
      );
    }
  };

  let title = "";
  let description = "";
  if (dialog.kind === "location") {
    title = "Add a location";
    description = "Give your storage space a name.";
  } else if (dialog.kind === "item") {
    title = `Add item to ${dialog.location.name}`;
    description = "Add something to this location.";
  } else if (dialog.kind === "move") {
    title = `Move ${dialog.item.name}`;
    description = "Choose where this item should live.";
  } else if (dialog.kind === "delete-item") {
    title = "Delete this item?";
    description = `“${dialog.item.name}” and its full quantity will be permanently deleted.`;
  } else {
    title = `Delete ${dialog.location.name}?`;
    description =
      deleteLocationItemCount > 0
        ? `This permanently deletes the location and all ${deleteLocationItemCount} item${deleteLocationItemCount === 1 ? "" : "s"} in it.`
        : "This permanently deletes the location.";
  }

  return (
    <div className="dialog-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !busy) onClose();
    }}>
      <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <div className="dialog-header">
          <div>
            <h2 id="dialog-title">{title}</h2>
            <p>{description}</p>
          </div>
          <button className="icon-button" aria-label="Close dialog" onClick={onClose} disabled={busy}>
            <X size={18} />
          </button>
        </div>

        {error && <div className="dialog-error" role="alert">{error}</div>}

        {dialog.kind === "delete-item" && actionItem ? (
          <div className="dialog-actions">
            <button className="button button-outline" onClick={onClose} disabled={busy}>Cancel</button>
            <button className="button button-danger" onClick={() => onDeleteItem(actionItem)} disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={16} /> : <Trash2 size={16} />}
              Delete item
            </button>
          </div>
        ) : dialog.kind === "delete-location" ? (
          <div className="dialog-actions">
            <button className="button button-outline" onClick={onClose} disabled={busy}>Keep location</button>
            <button className="button button-danger" onClick={() => onDeleteLocation(dialog.location)} disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={16} /> : <Trash2 size={16} />}
              {deleteLocationItemCount > 0 ? "Delete location and items" : "Delete location"}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {dialog.kind === "location" && (
              <label className="field">
                <span>Location name</span>
                <input name="name" placeholder="e.g. Garage" required autoFocus maxLength={200} />
              </label>
            )}
            {dialog.kind === "item" && (
              <>
                <label className="field">
                  <span>Item name</span>
                  <input name="name" placeholder="e.g. Camping lantern" required autoFocus maxLength={200} />
                </label>
                <label className="field">
                  <span>Description <em>optional</em></span>
                  <input name="description" placeholder="A short note about this item" maxLength={2000} />
                </label>
                <div className="form-row">
                  <label className="field">
                    <span>Quantity</span>
                    <input name="count" type="number" min="1" defaultValue="1" required />
                  </label>
                  <label className="field">
                    <span>Sub-location</span>
                    <select
                      name="sub_location_id"
                      value={selectedSubLocationId}
                      disabled={busy}
                      onChange={(event) => {
                        const value = event.target.value;
                        if (value === ADD_NEW_SUB_LOCATION) {
                          setSubLocationBeforeAdd(selectedSubLocationId);
                          setSelectedSubLocationId(ADD_NEW_SUB_LOCATION);
                          setCreatingSubLocation(true);
                        } else {
                          setSelectedSubLocationId(value);
                          setSubLocationBeforeAdd(value);
                          setCreatingSubLocation(false);
                          setSubLocationError("");
                        }
                      }}
                    >
                      {!selectedSubLocationId && (
                        <option value="" disabled>Select a sub-location</option>
                      )}
                      {subLocations.map((subLocation) => (
                        <option key={subLocation.id ?? subLocation.name} value={subLocation.id ?? ""}>{subLocation.name}</option>
                      ))}
                      <option value={ADD_NEW_SUB_LOCATION}>Add new…</option>
                    </select>
                  </label>
                </div>
                {creatingSubLocation && (
                  <div className="new-sublocation-panel">
                    <label className="field">
                      <span>New sub-location name</span>
                      <input
                        autoFocus
                        maxLength={200}
                        placeholder="e.g. Top shelf"
                        value={newSubLocationName}
                        onChange={(event) => setNewSubLocationName(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            void addSubLocation();
                          }
                        }}
                      />
                    </label>
                    {subLocationError && (
                      <p className="sub-location-error" role="alert">{subLocationError}</p>
                    )}
                    <div className="sub-location-actions">
                      <button
                        type="button"
                        className="button button-outline"
                        disabled={busy}
                        onClick={() => {
                          setSelectedSubLocationId(subLocationBeforeAdd);
                          setCreatingSubLocation(false);
                          setNewSubLocationName("");
                          setSubLocationError("");
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        className="button button-primary"
                        disabled={busy || !newSubLocationName.trim()}
                        onClick={() => void addSubLocation()}
                      >
                        {busy ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />}
                        Create &amp; use
                      </button>
                    </div>
                  </div>
                )}
                <p className="form-note">Adding an existing item name increases its quantity.</p>
              </>
            )}
            {dialog.kind === "move" && (
              <>
                <label className="field">
                  <span>Destination</span>
                  <select
                    name="location_id"
                    value={selectedLocationId ?? ""}
                    onChange={(event) => setSelectedLocationId(Number(event.target.value))}
                    required
                  >
                    {locations.map((location) => (
                      <option key={location.id ?? location.name} value={location.id ?? ""}>{location.name}</option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Sub-location</span>
                  <select
                    key={selectedLocationId}
                    name="sub_location_id"
                    defaultValue={defaultSubLocation ?? ""}
                  >
                    {subLocations.map((subLocation) => (
                      <option key={subLocation.id ?? subLocation.name} value={subLocation.id ?? ""}>{subLocation.name}</option>
                    ))}
                  </select>
                </label>
              </>
            )}
            <div className="dialog-actions">
              <button type="button" className="button button-outline" onClick={onClose} disabled={busy}>Cancel</button>
              <button
                type="submit"
                className="button button-primary"
                disabled={
                  busy ||
                  (dialog.kind === "move" && locations.length === 0) ||
                  (dialog.kind === "item" &&
                    (creatingSubLocation ||
                      selectedSubLocationId === ADD_NEW_SUB_LOCATION))
                }
              >
                {busy ? <LoaderCircle className="spin" size={16} /> : <Check size={16} />}
                {dialog.kind === "location" ? "Create location" : dialog.kind === "item" ? "Add item" : "Move item"}
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}

export default App;
