#!/usr/bin/env ruby
# Rename published GDS top cells to their release macro aliases.

require "fileutils"
require "json"

ROOT = File.expand_path("..", __dir__)
VARIANTS = [
  "gf180mcu_3v3_12t_2r2w_sram_512x8",
  "gf180mcu_3v3_12t_2r2w_sram_512x32",
  "gf180mcu_3v3_12t_2r2w_sram_1024x8",
  "gf180mcu_3v3_12t_2r2w_sram_1024x32"
].freeze

report = []

VARIANTS.each do |macro|
  gds = File.join(ROOT, "macros", macro, "layout", "#{macro}.gds")
  raise "missing GDS: #{gds}" unless File.file?(gds) && File.size(gds).positive?

  layout = RBA::Layout.new
  layout.read(gds)
  top_cells = layout.top_cells
  top_names = top_cells.map(&:name)
  old_name = nil
  status = nil

  if top_names.include?(macro)
    old_name = macro
    status = "already_public"
  elsif top_cells.length == 1
    top = top_cells.first
    old_name = top.name
    top.name = macro
    tmp = "#{gds}.tmp.gds"
    layout.write(tmp)
    FileUtils.mv(tmp, gds)
    status = "renamed"
  else
    raise "ambiguous top cells in #{gds}: #{top_names.join(', ')}"
  end

  report << {
    "macro" => macro,
    "gds" => gds.sub("#{ROOT}/", ""),
    "old_topcell" => old_name,
    "new_topcell" => macro,
    "status" => status
  }
end

out = File.join(ROOT, "reports", "final_physical", "gds_topcell_rewrite.json")
File.write(out, JSON.pretty_generate(report) + "\n")
puts "wrote #{out}"
