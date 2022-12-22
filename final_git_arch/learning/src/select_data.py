import os
import argparse
import zipfile
import pandas as pd
from io import BytesIO


def main(args):
    # Create destination zip
    dest = os.path.join(args.output, 'notes')
    if not os.path.exists(dest):
        os.makedirs(dest)

    # Load selection
    selection = pd.read_csv(args.selection_csv, sep='\t')
    print(selection)

    with zipfile.ZipFile(args.features_zip) as z:
        # For each score copy notes.tsv to the destination zip
        for i in selection.index:
            id = str(selection['ID'][i])
            filepath = 'features/' + id + '.zip'
            try:
                zfdata = BytesIO(z.read(filepath))
                with zipfile.ZipFile(zfdata) as zf:
                    zf.extract('notes.tsv', path=dest)
                    os.rename(os.path.join(dest, 'notes.tsv'), os.path.join(dest, id + '.tsv'))
                    print("Extracted notes for ID ", id)
            except:
                print('Could not extract ', filepath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Extract notes for selected composers.""")
    parser.add_argument('-f', '--features_zip', default='./features.zip')
    parser.add_argument('-o', '--output', default='./selected')
    parser.add_argument('-i', '--selection_csv', default='./selection.tsv')

    args = parser.parse_args()
    main(args)
