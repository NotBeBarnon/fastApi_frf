# -*- coding: utf-8 -*-
# @Time    : 2022/8/10 15:01
# @Author  : Tuffy
# @Description :
import enum
from typing import List, Literal, Union

from construct import Array, BitStruct, BitsInteger, Default, Flag, Int16ub, Int8ub, Rebuild, len_, this
from pydantic import Field

from src.my_tools.signalling_tools import PreSwitch, SignallingBaseModel


class DescriptorTagEnum(int, enum.Enum):
    linkage_descriptor = 0x4a
    correction_message_descriptor = 0xa1


class PopulationIdLoopModel(SignallingBaseModel):
    population_id_base: int = Field(..., description="", signalling_struct=Int16ub)
    population_id_mask: int = Field(..., description="", signalling_struct=Int16ub)


class LinkageDescriptorModel(SignallingBaseModel):
    descriptor_tag: Literal[DescriptorTagEnum.linkage_descriptor] = Field(
        DescriptorTagEnum.linkage_descriptor,
        description="描述符类型",
        signalling_struct=Int8ub,
    )
    descriptor_length: int = Field(..., description="描述符长度", signalling_struct=Rebuild(Int8ub, lambda con: len(con.population_id_loop) * 4 + 3))
    forward_multiplex: int = Field(..., description="前向多路复用", signalling_struct=Int16ub)
    population_id_loop_count: int = Field(0, description="population个数", signalling_struct=Rebuild(Int8ub, len_(this.population_id_loop)))
    population_id_loop: List[PopulationIdLoopModel] = Field(
        ...,
        description="population_id_loop",
        signalling_struct=Array(this.population_id_loop_count, PopulationIdLoopModel._signalling_struct),
    )


class CorrectionMessageDescriptorModel(SignallingBaseModel):
    _signalling_struct = BitStruct
    descriptor_tag: Literal[DescriptorTagEnum.correction_message_descriptor] = Field(
        DescriptorTagEnum.correction_message_descriptor,
        description="描述符类型",
        signalling_struct=BitsInteger(8),
    )
    descriptor_length: int = Field(5, description="描述符长度", signalling_struct=Default(BitsInteger(8), 1))
    time_correction_flag: bool = Field(False, description="时间校正标志", signalling_struct=Default(Flag, 0))
    power_section_flag: bool = Field(False, description="功率段标志", signalling_struct=Default(Flag, 0))
    frequency: int = Field(..., description="频率校正标志", signalling_struct=Default(BitsInteger(6), 0))


class TIMUUnicastTable(SignallingBaseModel):
    rcst_status: int = Field(..., description="RCST状态", signalling_struct=Int8ub)
    descriptor_loop_count: int = Field(..., description="描述符数量", signalling_struct=Rebuild(Int8ub, len_(this.descriptor_loop)))
    descriptor_loop: List[
        Union[
            CorrectionMessageDescriptorModel,
            LinkageDescriptorModel,
        ]
    ] = Field(
        ..., description="描述符列表",
        signalling_struct=Array(
            this.descriptor_loop_count,
            PreSwitch(
                "descriptor_tag", Int8ub,
                DescriptorTagEnum.correction_message_descriptor / CorrectionMessageDescriptorModel._signalling_struct,
                DescriptorTagEnum.linkage_descriptor / LinkageDescriptorModel._signalling_struct,
            )
        )
    )


if __name__ == '__main__':
    print(
        TIMUUnicastTable.signalling_build(
            {
                "rcst_status": 1,
                "descriptor_loop": [],
            }
        )
    )
