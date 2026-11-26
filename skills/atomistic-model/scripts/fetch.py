"""Fetch one selected C2DB UID or Materials Project ID as an editable atomic model."""
import argparse
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ase.data import atomic_numbers
from ase.io import read

from model import write_model


def mp_structure(entry):
    """Use the species definitions. OPTIMADE site labels may differ from element symbols."""
    from pymatgen.core import Lattice, Structure

    attrs = entry["attributes"]
    definitions = {d["name"]: d for d in attrs["species"]}
    sites = []
    if set(attrs["structure_features"]) & {"assemblies", "implicit_atoms", "site_attachments"}:
        raise ValueError("This entry needs an explicit atomic configuration before export")
    for label in attrs["species_at_sites"]:
        spec = definitions[label]
        if spec["concentration"] != [1.0] or len(spec["chemical_symbols"]) != 1:
            raise ValueError("Resolve partial occupancy into an explicit atomic configuration first")
        symbol, = spec["chemical_symbols"]
        if symbol not in atomic_numbers or symbol == "X":
            raise ValueError(f"Expected a real element for site label {label}")
        sites.append(symbol)
    if len(sites) != attrs["nsites"]:
        raise ValueError("Site count disagrees with OPTIMADE nsites")
    lattice = Lattice(attrs["lattice_vectors"], pbc=tuple(bool(i) for i in attrs["dimension_types"]))
    return Structure(lattice, sites, attrs["cartesian_site_positions"], coords_are_cartesian=True)


def fetch(provider, entry_id, destination):
    if provider == "c2db":
        if not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+", entry_id):
            raise ValueError("Use the C2DB UID shown on the selected entry page")
        page = f"https://c2db.fysik.dtu.dk/material/{entry_id}"
        url = page + "/download/xyz"
    elif provider == "mp":
        if not re.fullmatch(r"mp-[0-9]+", entry_id):
            raise ValueError("Use a Materials Project ID such as mp-149")
        page = f"https://materialsproject.org/materials/{entry_id}"
        url = f"https://optimade.materialsproject.org/v1/structures/{entry_id}"
    else:
        raise ValueError(f"Unknown provider {provider}")

    accept = "application/json" if provider == "mp" else "*/*"
    request = Request(url, headers={"User-Agent": "atomistic-model/1.0 (scientific structure retrieval)",
                                    "Accept": accept})
    with urlopen(request, timeout=30) as response:
        payload = response.read()
    source = dict(database=provider, id=entry_id, entry_url=page, download_url=url,
                  retrieved_utc=datetime.now(timezone.utc).date().isoformat(),
                  sha256=hashlib.sha256(payload).hexdigest())
    if provider == "c2db":
        model = read(StringIO(payload.decode()), format="extxyz")
        if sum(model.pbc) != 2:
            raise ValueError("Expected two periodic axes in the C2DB monolayer download")
    else:
        entry = json.loads(payload)["data"]
        if not entry or entry["type"] != "structures" or entry["id"] != entry_id:
            raise ValueError(f"MP did not return the requested structure {entry_id}")
        model = mp_structure(entry)
        source["last_modified"] = entry["attributes"].get("last_modified")
    return write_model(model, destination, source=source)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider", choices=("c2db", "mp"))
    parser.add_argument("entry_id")
    parser.add_argument("output")
    args = parser.parse_args()
    try:
        result = fetch(args.provider, args.entry_id, args.output)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        parser.exit(1, f"{args.provider} {args.entry_id}: {exc}\n")
    print(f"{result.get_chemical_formula()} · {len(result)} sites -> {args.output}")
