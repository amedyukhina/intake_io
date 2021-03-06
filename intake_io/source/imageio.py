import numpy as np
import imageio
import intake
from typing import Optional
from .bioformats import BioformatsSource


class ImageIOSource(intake.source.base.DataSource):
    """Intake source using imageio as backend.

    Attributes:
        uri (str): URI (e.g. file system path or URL)
    """

    container = "ndarray"
    name = "imageio"
    version = "0.0.1"
    partition_access = True

    def __init__(self, uri: str, metadata: Optional[dict] = None):
        """
        Arguments:
            uri (str): URI (e.g. file system path or URL)
            metadata (dict, optional): Extra metadata, handed over to intake
        """
        super().__init__(metadata=metadata)
        self.uri = uri
        self._reader = None

    def _get_schema(self) -> intake.source.base.Schema:
        if self._reader is None:
            self._reader = imageio.get_reader(self.uri)
        im = self._reader.get_data(0)
        assert im.ndim == 2 or im.ndim == 3 and im.shape[-1] == 3
        #if im.shape[-1] == 3:
        #    self._img = np.transpose(self._img, (2,0,1))

        fileheader = self._reader.get_meta_data()
        if fileheader["is_ome"]:
            s = BioformatsSource._static_get_schema(fileheader["description"])
            s.npartitions = self._reader.get_length()
            return s

        shape = tuple(im.shape) if self._reader.get_length() == 1 else (self._reader.get_length(), *im.shape)
        return intake.source.base.Schema(
            datashape=shape,
            shape=shape,
            dtype=im.dtype,
            npartitions=self._reader.get_length(),
            chunks=None,
            extra_metadata=dict(
                axes=None,
                spacing=None,
                spacing_units=None,
                coords=None,
                fileheader=fileheader
            )
        )

    def read(self) -> np.ndarray:
        self._load_metadata()
        if self.npartitions == 1:
            return self.read_partition(0)
        out = np.zeros(self.shape, self.dtype)
        for i in range(out.shape[0]):
            out[i] = self.read_partition(i)
        return out

    def _get_partition(self, i: int) -> np.ndarray:
        out = self._reader.get_data(i)
        if out.ndim == 3 and out.shape[-1] == 3:
            out = out.transpose(2, 0, 1)
        return out

    def _close(self):
        if self._reader is not None:
            self._reader.close()
