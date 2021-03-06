from aiida.engine import CalcJob
from aiida.common import CalcInfo, CodeInfo
from aiida.plugins import DataFactory
from aiida.orm import Bool
from aiida_phonopy.common.file_generators import get_BORN_txt

Dict = DataFactory('dict')
StructureData = DataFactory('structure')
ArrayData = DataFactory('array')


class BasePhonopyCalculation(CalcJob):
    """
    A basic plugin for calculating force constants using Phonopy.
    Requirement: the node should be able to import phonopy if NAC is used
    """

    _INPUT_NAC = 'BORN'

    @classmethod
    def define(cls, spec):
        """

        dataset : Dict, ArrayData, optional
            In Dict, this is similar to phonopy.dataset. This can be either
            type-I or type-II. In ArrayData, this can contain arrays of forces
            and displacements like type-II phonopy dataset, for which the array
            names are 'forces' and 'displacements'.

        """

        super().define(spec)

        spec.input('settings', valid_type=Dict,
                   help='Phonopy parameters')
        spec.input('structure', valid_type=StructureData,
                   help='Unit cell structure')
        spec.input('fc_only', valid_type=Bool,
                   help='Only force constants are calculated.',
                   default=lambda: Bool(False))
        spec.input('force_sets', valid_type=ArrayData, required=False,
                   help='Sets of forces in supercells')
        spec.input('dataset', valid_type=ArrayData, required=False,
                   help='Sets of displacements and forces in supercells')
        spec.input('nac_params', valid_type=ArrayData, required=False,
                   help='NAC parameters')
        spec.input('primitive', valid_type=StructureData, required=False,
                   help='Primitive cell structure')
        spec.input('dataset', valid_type=(Dict, ArrayData), required=False,
                   help='Displacements and forces dataset')
        spec.inputs['metadata']['options']['withmpi'].default = False

    def prepare_for_submission(self, folder):
        """Create the input files from the input nodes passed to this instance of the `CalcJob`.

        :param folder: an `aiida.common.folders.Folder` to temporarily write files on disk
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        self.logger.info("prepare_for_submission")

        # These three lists are updated in self._create_additional_files(folder)
        self._internal_retrieve_list = []
        self._additional_cmd_params = []
        self._calculation_cmd = []
        self._create_additional_files(folder)

        # ================= prepare the python input files =================

        # BORN
        if (not self.inputs.fc_only and
            'nac_params' in self.inputs and
            'primitive' in self.inputs and
            'symmetry_tolerance' in self.inputs.settings.attributes):
            born_txt = get_BORN_txt(
                self.inputs.nac_params,
                self.inputs.primitive,
                self.inputs.settings['symmetry_tolerance'])
            with folder.open(self._INPUT_NAC, 'w', encoding='utf8') as handle:
                handle.write(born_txt)
            for params in self._additional_cmd_params:
                params.append('--nac')

        # ============================ calcinfo ===============================

        local_copy_list = []
        remote_copy_list = []

        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.retrieve_list = self._internal_retrieve_list

        calcinfo.codes_info = []
        for i, (default_params, additional_params) in enumerate(zip(
                self._calculation_cmd, self._additional_cmd_params)):
            codeinfo = CodeInfo()
            codeinfo.cmdline_params = default_params + additional_params
            codeinfo.code_uuid = self.inputs.code.uuid
            codeinfo.stdout_name = "%s%d" % (
                self.options.output_filename, i + 1)
            codeinfo.withmpi = False
            calcinfo.codes_info.append(codeinfo)

        return calcinfo

    def _create_additional_files(self, folder):
        raise NotImplementedError()
