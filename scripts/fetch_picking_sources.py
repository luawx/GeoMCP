"""Fetch immutable official source snapshots; excludes bulk data, weights and git metadata."""
import hashlib, io, json, pathlib, urllib.request, zipfile
ROOT = pathlib.Path(__file__).resolve().parents[1] / 'third_party'
REPOS = {'phasenet':('AI4EPS/PhaseNet','62005c6195638f88d077f8870ea895971062715a'),'eqnet':('AI4EPS/EQNet','7dd24edd275b914115c0c6bdf2c329517f61efc8'),'obspy':('obspy/obspy','50033e1daf95233cd4f30e95a49c37fd50be2ccd')}

def main():
    for name, (repo, commit) in REPOS.items():
        raw = urllib.request.urlopen(f'https://codeload.github.com/{repo}/zip/{commit}').read()
        target = ROOT / name
        target.mkdir(parents=True,exist_ok=True)
        hashes = {}
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for info in z.infolist():
                rel = pathlib.PurePosixPath(*pathlib.PurePosixPath(info.filename).parts[1:])
                if info.is_dir() or not rel.parts or any(p in {'.git','datasets','dataset','testdata','tests','docs','examples','notebooks','checkpoints'} for p in rel.parts[:-1]) or rel.suffix.lower() in {'.h5','.hdf5','.mseed','.png','.jpg','.jpeg','.gif','.ipynb','.pth','.pt','.ckpt','.pdf','.npy','.npz'}:
                    continue
                if name == 'phasenet' and rel.parts[0] == 'model':
                    continue
                if '..' in rel.parts or info.file_size > 2_000_000:
                    continue
                payload = z.read(info)
                out = target.joinpath(*rel.parts)
                out.parent.mkdir(parents=True,exist_ok=True)
                out.write_bytes(payload)
                hashes[str(rel)] = hashlib.sha256(payload).hexdigest()
        (target/'PROVENANCE.json').write_text(json.dumps({'repository':f'https://github.com/{repo}','commit':commit,'archive_sha256':hashlib.sha256(raw).hexdigest(),'files_sha256':hashes,'excluded':'bulk data, tests/docs/examples, binaries, weights; source-only snapshot'},indent=2)+'\n')
        print(name,commit,len(hashes),flush=True)
if __name__ == '__main__': main()
