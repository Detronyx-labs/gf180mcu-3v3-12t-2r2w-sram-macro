#!/usr/bin/env ruby
# Add physical M2/M3 top-level routing for the stdcell control/predecode matrix.

require "csv"
require "fileutils"
require "json"
require "rexml/document"

ROOT = File.expand_path("..", __dir__)
FINAL_MANIFEST = File.join(ROOT, "reports", "final_physical", "MANIFEST.json")
CONTROL_MANIFEST = File.join(ROOT, "reports", "stdcell_control_placement", "MANIFEST.json")
ROWSEL_MANIFEST = File.join(ROOT, "reports", "stdcell_row_select_placement", "MANIFEST.json")
OUT = File.join(ROOT, "reports", "stdcell_control_signal_routing")

LAYER_M1 = [34, 0].freeze
LAYER_V1 = [35, 0].freeze
LAYER_M2 = [36, 0].freeze
LAYER_V2 = [38, 0].freeze
LAYER_M3 = [42, 0].freeze
LAYER_V3 = [40, 0].freeze
LAYER_M4 = [46, 0].freeze
GRID_UM = 0.005
WIRE_W = 0.28
PAD_W = 0.38
VIA_W = 0.22

PIN_ORDER = {
  "gf180mcu_as_sc_mcu7t3v3__inv_2" => %w[VDD VNW VPW VSS Y A],
  "gf180mcu_as_sc_mcu7t3v3__nand2_2" => %w[VDD VNW VPW VSS Y B A],
  "gf180mcu_as_sc_mcu7t3v3__nand3_2" => %w[VDD VNW VPW VSS A B C Y],
  "gf180mcu_as_sc_mcu7t3v3__nand4_2" => %w[VDD VNW VPW VSS A B C D Y],
  "gf180mcu_as_sc_mcu7t3v3__nor2_2" => %w[VDD VNW VPW VSS Y B A]
}.freeze

# Pin centers are chosen inside LEF Metal1 pin rectangles.  For multi-input
# NAND cells the y-points are separated where possible so same-row M2 taps do
# not collapse into one broad conductor.
PIN_ANCHORS = {
  "gf180mcu_as_sc_mcu7t3v3__inv_2" => {
    "A" => [0.49, 1.86],
    "Y" => [1.12, 1.92]
  },
  "gf180mcu_as_sc_mcu7t3v3__nand2_2" => {
    "A" => [1.08, 1.72],
    "B" => [2.53, 1.92],
    "Y" => [3.40, 2.05]
  },
  "gf180mcu_as_sc_mcu7t3v3__nand3_2" => {
    "A" => [0.90, 1.68],
    "B" => [2.62, 1.90],
    "C" => [4.38, 2.22],
    "Y" => [5.00, 2.10]
  },
  "gf180mcu_as_sc_mcu7t3v3__nand4_2" => {
    "A" => [0.90, 1.68],
    "B" => [2.62, 1.90],
    "C" => [4.38, 1.78],
    "D" => [5.98, 2.28],
    "Y" => [6.66, 1.95]
  },
  "gf180mcu_as_sc_mcu7t3v3__nor2_2" => {
    "A" => [1.08, 1.72],
    "B" => [2.53, 1.92],
    "Y" => [3.40, 1.70]
  }
}.freeze

PORT_INDEX = { "w0" => 0, "w1" => 1, "r0" => 2, "r1" => 3 }.freeze
ROWSEL_LOCAL_X = { "A" => 0.90, "B" => 2.62, "C" => 4.38, "D" => 5.98 }.freeze
ROWSEL_OFFSETS = [-0.30, -0.10, 0.10, 0.30].freeze
POWER_NETS = %w[VDD VSS VNW VPW].freeze

Endpoint = Struct.new(:net, :inst, :pin, :cell, :x, :y, :kind, keyword_init: true)

def rel(path)
  path.sub("#{ROOT}/", "")
end

def snap_um(value)
  (value.to_f / GRID_UM).round * GRID_UM
end

def dbu(layout, value_um)
  (snap_um(value_um) / layout.dbu).round
end

def layer(layout, pair)
  layout.layer(pair[0], pair[1])
end

def box_um(layout, x0, y0, x1, y1)
  RBA::Box.new(dbu(layout, x0), dbu(layout, y0), dbu(layout, x1), dbu(layout, y1))
end

def add_rect(cell, layout, pair, x0, y0, x1, y1)
  return 0 if x1 <= x0 || y1 <= y0
  cell.shapes(layer(layout, pair)).insert(box_um(layout, x0, y0, x1, y1))
  1
end

def add_square(cell, layout, pair, x, y, size)
  half = size / 2.0
  add_rect(cell, layout, pair, x - half, y - half, x + half, y + half)
end

def add_pin_to_m2_stack(cell, layout, x, y)
  count = 0
  count += add_square(cell, layout, LAYER_M1, x, y, PAD_W)
  count += add_square(cell, layout, LAYER_V1, x, y, VIA_W)
  count += add_square(cell, layout, LAYER_M2, x, y, PAD_W)
  count
end

def add_m2_to_m3_stack(cell, layout, x, y)
  count = 0
  count += add_square(cell, layout, LAYER_M2, x, y, PAD_W)
  count += add_square(cell, layout, LAYER_V2, x, y, VIA_W)
  count += add_square(cell, layout, LAYER_M3, x, y, PAD_W)
  count
end

def add_m4_pin_to_m2_stack(cell, layout, x, y)
  count = 0
  count += add_square(cell, layout, LAYER_M4, x, y, PAD_W)
  count += add_square(cell, layout, LAYER_V3, x, y, VIA_W)
  count += add_square(cell, layout, LAYER_M3, x, y, PAD_W)
  count += add_square(cell, layout, LAYER_V2, x, y, VIA_W)
  count += add_square(cell, layout, LAYER_M2, x, y, PAD_W)
  count
end

def add_m2_wire(cell, layout, x0, y0, x1, y1)
  return add_square(cell, layout, LAYER_M2, x0, y0, PAD_W) if (x1 - x0).abs < 0.001 && (y1 - y0).abs < 0.001

  if (x1 - x0).abs >= (y1 - y0).abs
    add_rect(cell, layout, LAYER_M2, [x0, x1].min, y0 - WIRE_W / 2.0, [x0, x1].max, y0 + WIRE_W / 2.0)
  else
    add_rect(cell, layout, LAYER_M2, x0 - WIRE_W / 2.0, [y0, y1].min, x0 + WIRE_W / 2.0, [y0, y1].max)
  end
end

def add_m3_vertical(cell, layout, x, y0, y1)
  add_rect(cell, layout, LAYER_M3, x - WIRE_W / 2.0, [y0, y1].min, x + WIRE_W / 2.0, [y0, y1].max)
end

def find_cell(layout, name)
  if layout.respond_to?(:cell_by_name)
    begin
      value = layout.cell_by_name(name)
      return value if value.respond_to?(:name)
      return layout.cell(value) if value.is_a?(Integer) && value >= 0
    rescue StandardError
      nil
    end
  end
  begin
    value = layout.cell(name)
    return value if value.respond_to?(:name)
    return layout.cell(value) if value.is_a?(Integer) && value >= 0
  rescue StandardError
    nil
  end
  layout.each_cell { |cell| return cell if cell.name == name }
  nil
end

def remove_existing_route_cell(layout, top, route_name)
  old = find_cell(layout, route_name)
  return unless old

  top.each_inst do |inst|
    inst.delete if inst.cell_index == old.cell_index
  end
  [LAYER_M1, LAYER_V1, LAYER_M2, LAYER_V2, LAYER_M3, LAYER_V3, LAYER_M4].each do |pair|
    old.shapes(layer(layout, pair)).clear
  end
end

def bbox_um(cell, layout)
  box = cell.bbox
  {
    "left_um" => (box.left * layout.dbu).round(6),
    "bottom_um" => (box.bottom * layout.dbu).round(6),
    "right_um" => (box.right * layout.dbu).round(6),
    "top_um" => (box.top * layout.dbu).round(6),
    "width_um" => (box.width * layout.dbu).round(6),
    "height_um" => (box.height * layout.dbu).round(6)
  }
end

def read_csv(path)
  CSV.read(path, headers: true).map(&:to_h)
end

def build_placement(control_csv, rowsel_csv)
  placement = {}
  read_csv(control_csv).each { |row| placement[row.fetch("name")] = row }
  read_csv(rowsel_csv).each { |row| placement[row.fetch("name")] = row }
  placement
end

def transform_anchor(row, local_x, local_y)
  x = row.fetch("x_um").to_f
  y = row.fetch("y_um").to_f
  width = row.fetch("width_um").to_f
  height = row.fetch("height_um").to_f
  case row.fetch("orient")
  when "N"
    [x + local_x, y + local_y]
  when "S"
    [x + width - local_x, y + height - local_y]
  when "FN"
    [x + width - local_x, y + local_y]
  when "FS"
    [x + local_x, y + height - local_y]
  else
    raise "unsupported orientation #{row.fetch('orient').inspect} for #{row.fetch('name')}"
  end
end

def parse_cdl_endpoints(cdl_path, placement)
  endpoints = Hash.new { |hash, key| hash[key] = [] }
  File.readlines(cdl_path, chomp: true).each do |raw|
    line = raw.strip
    next unless line.start_with?("X")
    toks = line.split
    next if toks.length < 3
    inst = toks[0]
    cell = toks[-1]
    order = PIN_ORDER[cell]
    next unless order
    row = placement[inst]
    raise "missing placement for #{inst} from #{cdl_path}" unless row
    nets = toks[1...-1]
    raise "pin/net mismatch for #{inst}: #{nets.length} nets vs #{order.length} pins" unless nets.length == order.length

    order.zip(nets).each do |pin, net|
      next if POWER_NETS.include?(pin) || POWER_NETS.include?(net)
      anchor = PIN_ANCHORS.fetch(cell)[pin]
      next unless anchor
      x, y = transform_anchor(row, anchor[0], anchor[1])
      endpoints[net] << Endpoint.new(net: net, inst: inst, pin: pin, cell: cell, x: x, y: y, kind: "stdcell")
    end
  end
  endpoints
end

def add_external_pin_endpoints(endpoints, pins_json)
  pins = JSON.parse(File.read(pins_json))
  pins.each do |pin|
    next unless pin.fetch("use") == "SIGNAL"
    name = pin.fetch("name")
    next unless endpoints.key?(name)
    rect = pin.fetch("rect_um")
    x = (rect[0].to_f + rect[2].to_f) / 2.0
    y = (rect[1].to_f + rect[3].to_f) / 2.0
    endpoints[name] << Endpoint.new(net: name, inst: "PIN:#{name}", pin: name, cell: pin.fetch("layer"), x: x, y: y, kind: "macro_pin")
  end
end

def row_select_internal_net?(net)
  !!(net =~ /_(row\d+_sel_(row_n|buf0|buf1))$/)
end

def row_select_input_track(net, endpoint, final_item)
  match = net.match(/\A(?<port>w0|w1|r0|r1)_(?<which>pd0|pd1|pd2)_(?<idx>[0-3])\z/)
  if match
    pin = { "pd0" => "A", "pd1" => "B", "pd2" => "C" }.fetch(match[:which])
    port_base = final_item.fetch("predecode_width_um").to_f + PORT_INDEX.fetch(match[:port]) * final_item.fetch("port_strip_width_um").to_f
    row_x = endpoint.x - ROWSEL_LOCAL_X.fetch(pin)
    nominal_row_x = port_base + 0.56
    base = (row_x - nominal_row_x).abs < 0.5 ? row_x : nominal_row_x
    return snap_um(base + ROWSEL_LOCAL_X.fetch(pin) + ROWSEL_OFFSETS[match[:idx].to_i])
  end

  match = net.match(/\A(?<port>w0|w1|r0|r1)_en\z/)
  if match
    port_base = final_item.fetch("predecode_width_um").to_f + PORT_INDEX.fetch(match[:port]) * final_item.fetch("port_strip_width_um").to_f
    base = port_base + 0.56
    return snap_um(base + ROWSEL_LOCAL_X.fetch("D") + 0.34)
  end
  nil
end

def track_for_net(net, endpoints, final_item, ordinary_index)
  rowsel_ep = endpoints.find { |ep| ep.inst =~ /_row\d+_sel_nand[34]\z/ && %w[A B C D].include?(ep.pin) }
  if rowsel_ep
    value = row_select_input_track(net, rowsel_ep, final_item)
    return value if value
  end
  x0 = 1.55
  pitch = 0.68
  snap_um(x0 + ordinary_index * pitch)
end

def route_net(cell, layout, net, endpoints, track_x)
  shapes = 0
  ys = endpoints.map(&:y)
  y0 = ys.min - 0.25
  y1 = ys.max + 0.25
  shapes += add_m3_vertical(cell, layout, track_x, y0, y1)
  endpoints.each do |ep|
    if ep.kind == "macro_pin"
      shapes += add_m4_pin_to_m2_stack(cell, layout, ep.x, ep.y)
    else
      shapes += add_pin_to_m2_stack(cell, layout, ep.x, ep.y)
    end
    shapes += add_m2_wire(cell, layout, ep.x, ep.y, track_x, ep.y)
    shapes += add_m2_to_m3_stack(cell, layout, track_x, ep.y)
  end
  shapes
end

def lyrdb_items(path)
  return nil unless File.file?(path)
  doc = REXML::Document.new(File.read(path))
  items = doc.root&.elements&.[]("items")
  return nil unless items
  items.elements.to_a.length
end

raise "missing final manifest" unless File.file?(FINAL_MANIFEST)
raise "missing control placement manifest" unless File.file?(CONTROL_MANIFEST)
raise "missing row-select placement manifest" unless File.file?(ROWSEL_MANIFEST)

FileUtils.mkdir_p(OUT)
final_by_macro = JSON.parse(File.read(FINAL_MANIFEST)).to_h { |item| [item.fetch("macro"), item] }
control_by_macro = JSON.parse(File.read(CONTROL_MANIFEST)).fetch("results").to_h { |item| [item.fetch("macro"), item] }
rowsel_by_macro = JSON.parse(File.read(ROWSEL_MANIFEST)).fetch("results").to_h { |item| [item.fetch("macro"), item] }
results = []

final_by_macro.keys.sort.each do |macro|
  final_item = final_by_macro.fetch(macro)
  control_item = control_by_macro.fetch(macro)
  rowsel_item = rowsel_by_macro.fetch(macro)
  macro_gds = File.join(ROOT, "macros", macro, "layout", "#{macro}.gds")
  pins_json = File.join(ROOT, "macros", macro, "abstract", "#{macro}.pins.json")
  cdl = File.join(ROOT, rowsel_item.fetch("macro_expanded_cdl"))
  placement = build_placement(File.join(ROOT, control_item.fetch("placement_csv")), File.join(ROOT, rowsel_item.fetch("placement_csv")))
  endpoints = parse_cdl_endpoints(cdl, placement)
  add_external_pin_endpoints(endpoints, pins_json)

  candidate_nets = endpoints.keys.reject do |net|
    POWER_NETS.include?(net) || row_select_internal_net?(net) || endpoints[net].length < 2
  end.sort

  layout = RBA::Layout.new
  layout.read(macro_gds)
  top = find_cell(layout, macro)
  raise "missing top cell #{macro}" unless top
  bbox_before = bbox_um(top, layout)
  route_name = "#{macro}_stdcell_control_signal_routes"
  remove_existing_route_cell(layout, top, route_name)
  route_cell = find_cell(layout, route_name) || layout.create_cell(route_name)

  ordinary_index = 0
  routed = []
  total_shapes = 0
  candidate_nets.each do |net|
    eps = endpoints.fetch(net)
    track_x = track_for_net(net, eps, final_item, ordinary_index)
    ordinary_index += 1 unless eps.any? { |ep| ep.inst =~ /_row\d+_sel_nand[34]\z/ }
    shapes = route_net(route_cell, layout, net, eps, track_x)
    total_shapes += shapes
    routed << {
      "net" => net,
      "endpoints" => eps.length,
      "track_x_um" => track_x.round(6),
      "has_macro_pin" => eps.any? { |ep| ep.kind == "macro_pin" },
      "has_row_select_sink" => eps.any? { |ep| ep.inst =~ /_row\d+_sel_nand[34]\z/ },
      "shapes" => shapes
    }
  end

  top.insert(RBA::CellInstArray.new(route_cell.cell_index, RBA::Trans.new(RBA::Trans::R0, 0, 0)))
  bbox_after = bbox_um(top, layout)
  footprint = (bbox_after.fetch("width_um") - final_item.fetch("width_um").to_f).abs <= 0.001 &&
              (bbox_after.fetch("height_um") - final_item.fetch("height_um").to_f).abs <= 0.001 &&
              bbox_after.fetch("left_um").abs <= 0.001 &&
              bbox_after.fetch("bottom_um").abs <= 0.001
  status = footprint && routed.length.positive? ? "PASS" : "FAIL"
  if status == "PASS"
    tmp = "#{macro_gds}.tmp_control_signal_routes.gds"
    layout.write(tmp)
    FileUtils.mv(tmp, macro_gds)
  end

  row_select_nets = routed.count { |item| item.fetch("has_row_select_sink") }
  macro_pin_nets = routed.count { |item| item.fetch("has_macro_pin") }
  out_dir = File.join(OUT, macro)
  FileUtils.mkdir_p(out_dir)
  CSV.open(File.join(out_dir, "#{macro}.routed_nets.csv"), "w") do |csv|
    csv << %w[net endpoints track_x_um has_macro_pin has_row_select_sink shapes]
    routed.each { |row| csv << [row["net"], row["endpoints"], row["track_x_um"], row["has_macro_pin"], row["has_row_select_sink"], row["shapes"]] }
  end

  results << {
    "macro" => macro,
    "status" => status,
    "gds" => rel(macro_gds),
    "route_cell" => route_name,
    "expanded_cdl" => rel(cdl),
    "routed_nets" => routed.length,
    "routed_endpoints" => routed.sum { |item| item.fetch("endpoints") },
    "row_select_input_nets" => row_select_nets,
    "macro_pin_nets" => macro_pin_nets,
    "route_shapes" => total_shapes,
    "routed_nets_csv" => rel(File.join(out_dir, "#{macro}.routed_nets.csv")),
    "footprint_unchanged" => footprint,
    "bbox_before_um" => bbox_before,
    "bbox_after_um" => bbox_after,
    "detail" => status == "PASS" ? [] : ["footprint changed or no routed nets"]
  }
end

status = results.all? { |item| item.fetch("status") == "PASS" } ? "PASS" : "FAIL"
manifest = {
  "package" => "gf180mcu-3v3-12t-2r2w-sram-macro",
  "status" => status,
  "scope" => "top-level M2/M3 routed stdcell control, predecode, enable, and row-select input signal network",
  "final_physical_manifest" => rel(FINAL_MANIFEST),
  "control_placement_manifest" => rel(CONTROL_MANIFEST),
  "row_select_placement_manifest" => rel(ROWSEL_MANIFEST),
  "results" => results
}
File.write(File.join(OUT, "MANIFEST.json"), JSON.pretty_generate(manifest) + "\n")

lines = [
  "# Stdcell Control Signal Routing",
  "",
  "Top-level M2/M3 routes connect the expanded Avalon control/predecode netlist endpoints, including macro address/enable pins and row-select NAND input sinks.",
  "The route geometry is emitted into one idempotent child route cell per macro, instantiated at the top level without changing the macro footprint.",
  "",
  "| Macro | Status | Routed nets | Routed endpoints | Row-select input nets | Macro-pin nets | Route shapes | Footprint |",
  "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"
]
results.each do |item|
  lines << "| `#{item.fetch('macro')}` | `#{item.fetch('status')}` | #{item.fetch('routed_nets')} | #{item.fetch('routed_endpoints')} | #{item.fetch('row_select_input_nets')} | #{item.fetch('macro_pin_nets')} | #{item.fetch('route_shapes')} | `#{item.fetch('footprint_unchanged')}` |"
end
smoke_report = File.join(OUT, "gf180mcu_3v3_12t_2r2w_sram_512x8", "main_drc.lyrdb")
smoke_items = lyrdb_items(smoke_report)
unless smoke_items.nil?
  lines += [
    "",
    "Smoke DRC:",
    "",
    "- `gf180mcu_3v3_12t_2r2w_sram_512x8`: GF180 KLayout `main.drc` #{smoke_items.zero? ? 'PASS' : 'FAIL'}, `#{smoke_items}` violations, report `#{rel(smoke_report)}`."
  ]
end
File.write(File.join(OUT, "README.md"), lines.join("\n") + "\n")

puts "GF180MCU 12T SRAM stdcell control signal routing: #{status}"
puts File.join(OUT, "MANIFEST.json")
exit(status == "PASS" ? 0 : 1)
